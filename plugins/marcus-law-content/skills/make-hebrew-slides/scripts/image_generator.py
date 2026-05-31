"""
image_generator.py — יצירת תמונות באמצעות KIE.AI API לשימוש במצגות.

API: https://docs.kie.ai
- POST /api/v1/jobs/createTask    — שליחת משימה (מחזיר taskId)
- GET  /api/v1/jobs/recordInfo    — בדיקת סטטוס + URL לתוצאה

זרימה:
    generator = KieImageGenerator()
    image_path = generator.generate(
        prompt="...",
        model="google/imagen4-fast",
        aspect_ratio="16:9",
        output_dir="/tmp/images",
    )
    # מחזיר נתיב לקובץ PNG מקומי, מוכן להוספה למצגת.

תמיכה במודלים שונים: לכל מודל יש טווח פרמטרים שונה ב-input. המודול
ממפה אספקטים ופורמטים לערכים שהמודל מקבל.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

import requests

try:
    from . import config  # type: ignore
except ImportError:
    # תמיכה ב-import ישיר (כשמריצים את הסקריפט מחוץ לפקג')
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import config  # type: ignore


# ====================================================================
# Aspect-ratio mapping per model
# ====================================================================
# כל מודל מקבל פרמטרים שונים ל-aspect ratio. המיפוי הזה מנרמל את הקלט
# מ"16:9" / "1:1" / "9:16" / "4:3" / "3:2" לפרמטרים של המודל הספציפי.
#
# חשוב — המבנים נבדקו לפי תיעוד kie.ai (נכון לדצמבר 2025). אם מודל מסוים
# לא מקבל aspect מסוים, נחזיר שגיאה ידידותית.

ASPECT_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3"]


def _build_input(model: str, prompt: str, aspect_ratio: str,
                 extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """בונה את אובייקט ה-input לפי המודל הספציפי."""
    extra = extra or {}

    # google/nano-banana — שדה image_size
    if model.startswith("google/nano-banana"):
        return {
            "prompt": prompt,
            "output_format": "png",
            "image_size": aspect_ratio,
            **extra,
        }

    # google/imagen4* — שדה aspect_ratio
    if model.startswith("google/imagen4"):
        return {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
            **extra,
        }

    # bytedance/seedream / seedream-v4 — שדה image_size
    if "seedream" in model:
        return {
            "prompt": prompt,
            "image_size": aspect_ratio,
            **extra,
        }

    # openai/gpt-image-2 — שדה size
    if "gpt-image" in model:
        # GPT Image מקבל סייז שונה. נבחר ברירות מחדל סבירות.
        size_map = {
            "1:1": "1024x1024",
            "16:9": "1536x1024",
            "9:16": "1024x1536",
            "4:3": "1280x1024",
            "3:4": "1024x1280",
        }
        return {
            "prompt": prompt,
            "size": size_map.get(aspect_ratio, "1024x1024"),
            **extra,
        }

    # ברירת מחדל — ננסה את הפורמט הנפוץ
    return {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        **extra,
    }


# ====================================================================
# KieImageGenerator
# ====================================================================

class KieImageGenerator:
    """ממשק ליצירת תמונות דרך kie.ai."""

    def __init__(self, api_key: Optional[str] = None,
                 base_url: Optional[str] = None):
        # סדר עדיפות: arg → env → config
        self.api_key = (
            api_key
            or os.environ.get("KIE_API_KEY")
            or config.KIE_API_KEY
        )
        if not self.api_key:
            raise RuntimeError(
                "KIE_API_KEY חסר. הגדר ב-scripts/config.py או בסביבה."
            )
        self.base_url = (base_url or config.KIE_BASE_URL).rstrip("/")

    # ---------- Low-level ----------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def create_task(self, model: str, prompt: str,
                    aspect_ratio: str = "16:9",
                    extra_input: Optional[Dict[str, Any]] = None) -> str:
        """שולח task חדש ומחזיר taskId."""
        if aspect_ratio not in ASPECT_RATIOS:
            raise ValueError(
                f"aspect_ratio '{aspect_ratio}' לא נתמך. "
                f"בחר אחד מ: {ASPECT_RATIOS}"
            )

        body = {
            "model": model,
            "input": _build_input(model, prompt, aspect_ratio, extra_input),
        }
        resp = requests.post(
            f"{self.base_url}/createTask",
            headers=self._headers(),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(
                f"kie.ai create_task נכשל: code={data.get('code')} "
                f"msg={data.get('msg')}"
            )
        task_id = (data.get("data") or {}).get("taskId")
        if not task_id:
            raise RuntimeError(f"לא התקבל taskId. תגובה: {data}")
        return task_id

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """מחזיר את הסטטוס המלא של המשימה."""
        resp = requests.get(
            f"{self.base_url}/recordInfo",
            headers=self._headers(),
            params={"taskId": task_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(
                f"kie.ai recordInfo נכשל: code={data.get('code')} "
                f"msg={data.get('msg')}"
            )
        return data.get("data") or {}

    def wait_for_result(self, task_id: str,
                        timeout: Optional[int] = None,
                        interval: Optional[int] = None) -> str:
        """מבצע פולינג עד הצלחה/כישלון. מחזיר URL של התמונה."""
        timeout = timeout if timeout is not None else config.POLL_TIMEOUT
        interval = interval if interval is not None else config.POLL_INTERVAL

        deadline = time.time() + timeout
        last_state = None

        while time.time() < deadline:
            info = self.get_status(task_id)
            state = info.get("state")

            if state != last_state:
                # מדפיסים שינוי סטטוס בלבד (לא בכל פעם)
                print(f"  [kie.ai] state={state}")
                last_state = state

            if state == "success":
                result_json = info.get("resultJson") or "{}"
                try:
                    parsed = json.loads(result_json)
                except json.JSONDecodeError:
                    raise RuntimeError(
                        f"resultJson אינו JSON תקין: {result_json}"
                    )
                urls = parsed.get("resultUrls") or []
                if not urls:
                    raise RuntimeError(f"אין resultUrls בתוצאה: {parsed}")
                return urls[0]

            if state == "fail":
                fail_msg = info.get("failMsg") or info.get("failCode") or "?"
                raise RuntimeError(f"kie.ai task נכשל: {fail_msg}")

            # waiting / queuing / generating — ממשיכים
            time.sleep(interval)

        raise TimeoutError(
            f"timeout אחרי {timeout}s; המשימה {task_id} עדיין לא הושלמה."
        )

    # ---------- High-level ----------

    def generate(self, prompt: str,
                 model: Optional[str] = None,
                 aspect_ratio: str = "16:9",
                 output_dir: Optional[str | Path] = None,
                 filename: Optional[str] = None,
                 extra_input: Optional[Dict[str, Any]] = None) -> Path:
        """
        יוצר תמונה ומוריד אותה לקובץ מקומי. מחזיר את הנתיב לקובץ.

        אספקט מומלץ:
          - "16:9" — תמונה לשקף מלא (רקע מצגת)
          - "1:1"  — תמונה מרובעת לצד טקסט
          - "4:3"  — תמונה רחבה לשקף עם תוכן
        """
        model = model or config.DEFAULT_IMAGE_MODEL

        print(f"  [kie.ai] שולח משימה למודל {model}, aspect={aspect_ratio}")
        task_id = self.create_task(model, prompt, aspect_ratio, extra_input)
        print(f"  [kie.ai] taskId={task_id}, ממתין לתוצאה...")

        url = self.wait_for_result(task_id)
        print(f"  [kie.ai] תמונה מוכנה, מוריד...")

        # קובע נתיב יעד
        out_dir = Path(output_dir) if output_dir else Path("/tmp/kie_images")
        out_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            filename = f"img_{uuid.uuid4().hex[:8]}.png"
        elif not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            filename = filename + ".png"

        target = out_dir / filename
        return self.download(url, target)

    @staticmethod
    def download(url: str, target_path: Path) -> Path:
        """מוריד URL לקובץ מקומי."""
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return target_path


# ====================================================================
# Quick helper
# ====================================================================

def generate_image(prompt: str, model: Optional[str] = None,
                   aspect_ratio: str = "16:9",
                   output_dir: Optional[str | Path] = None,
                   filename: Optional[str] = None) -> Path:
    """פונקציה מקוצרת — יצירת תמונה אחת בקריאה אחת."""
    gen = KieImageGenerator()
    return gen.generate(
        prompt=prompt,
        model=model,
        aspect_ratio=aspect_ratio,
        output_dir=output_dir,
        filename=filename,
    )
