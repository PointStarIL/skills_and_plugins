#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
בדיקות ל-preservation_check.py.

העיקר כאן הוא שכל אחת משש הבדיקות **נכשלת כשצריך**. סידור-מחדש שמאבד
פסקה ומדווח "עבר" גרוע מאין בדיקה בכלל, כי הוא מייצר ראיה שקרית לכך
שההחלטה נבדקה.

הרצה:  python3 tests/test_preservation_check.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import preservation_check as pc  # noqa: E402


ORIGINAL = [
    "הערר שלפנינו עוסק בבקשה לשימוש חורג במקרקעין הידועים כחלקה 42 בגוש 6789.",
    'בפסיקה נקבע כי "שימוש חורג מתכנית הוא חריג שיש לפרשו בצמצום, ואין להתירו אלא במקרים המתאימים".',
    "לעניין זה נפנה לעע\"מ 1234/20 ולערר 5678/21 שדנו בסוגיה דומה.",
    "בענייננו, המבקש לא הוכיח כי מתקיימים התנאים שנקבעו בסעיף 149 לחוק התכנון והבניה.",
    "סוף דבר, הערר נדחה. אין צו להוצאות.",
]


def build(paras):
    return list(paras)


class TestCleanReorder(unittest.TestCase):
    def test_identical_passes(self):
        f = pc.check_all(build(ORIGINAL), build(ORIGINAL))
        self.assertEqual(pc.status_of(f), "עבר", [x.message for x in f])

    def test_pure_reorder_passes(self):
        """סידור מחדש בלבד: אותן פסקאות בסדר אחר. זה בדיוק מה שמותר."""
        reordered = [ORIGINAL[0], ORIGINAL[2], ORIGINAL[1], ORIGINAL[3], ORIGINAL[4]]
        f = pc.check_all(build(ORIGINAL), reordered)
        self.assertEqual(pc.status_of(f), "עבר", [x.message for x in f])

    def test_allowed_connector_is_green_not_red(self):
        """מילת קישור מהרשימה הסגורה מותרת, ומתועדת כ-GREEN."""
        new = list(ORIGINAL)
        new[3] = "ובענייננו, " + ORIGINAL[3]
        f = pc.check_all(build(ORIGINAL), new)
        self.assertNotEqual(pc.status_of(f), "נכשל", [x.message for x in f])
        self.assertTrue(any(x.severity == "GREEN" and x.check == "6-connectors" for x in f),
                        "התוספת המותרת לא תועדה")


class TestEachCheckFires(unittest.TestCase):

    def _fail(self, new, check):
        f = pc.check_all(build(ORIGINAL), new)
        blocking = [x for x in f if x.severity in ("RED", "DOUBLE_RED")]
        self.assertEqual(pc.status_of(f), "נכשל",
                         "לא נכשל. ממצאים: " + str([x.message for x in f]))
        self.assertTrue(any(x.check == check for x in blocking),
                        "הבדיקה {0} לא ירתה. ירו: {1}".format(
                            check, {x.check for x in blocking}))

    def test_1_lost_paragraph(self):
        new = [p for p in ORIGINAL if p != ORIGINAL[2]]
        self._fail(new, "1-paragraphs")

    def test_1_invented_paragraph(self):
        new = list(ORIGINAL)
        new.insert(3, "זוהי פסקה חדשה לגמרי שהמודל המציא ואינה קיימת במקור כלל.")
        self._fail(new, "1-paragraphs")

    def test_2_quote_altered(self):
        new = list(ORIGINAL)
        new[1] = ('בפסיקה נקבע כי "שימוש חורג מתכנית הוא חריג שיש לפרשו בהרחבה, '
                  'ויש להתירו בכל מקרה מתאים".')
        self._fail(new, "2-quotes")

    def test_3_reference_lost(self):
        new = list(ORIGINAL)
        new[2] = 'לעניין זה נפנה לעע"מ 1234/20 שדן בסוגיה דומה.'
        self._fail(new, "3-refs")

    def test_3_reference_invented(self):
        """הסכנה החמורה: אסמכתא שהמודל הוסיף מדעתו."""
        new = list(ORIGINAL)
        new[2] = ('לעניין זה נפנה לעע"מ 1234/20, לערר 5678/21 '
                  'ולבג"ץ 9999/99 שדנו בסוגיה דומה.')
        self._fail(new, "3-refs")

    def test_4_operative_changed(self):
        new = list(ORIGINAL)
        new[4] = "סוף דבר, הערר מתקבל. אין צו להוצאות."
        f = pc.check_all(build(ORIGINAL), new)
        self.assertEqual(pc.status_of(f), "נכשל")
        self.assertTrue(any(x.severity == "DOUBLE_RED" for x in f),
                        "שינוי תוצאה אופרטיבית חייב להיות DOUBLE_RED")

    def test_6_disallowed_connector(self):
        """'ברי כי' משנה עוצמת קביעה ואינו ברשימה המותרת."""
        new = list(ORIGINAL)
        new[3] = "ברי כי " + ORIGINAL[3]
        self._fail(new, "6-connectors")


class TestWarnings(unittest.TestCase):
    def test_5_length_drift_warns_but_does_not_block(self):
        """
        קיצור פסקה בלי לאבד ציטוט או הפניה הוא חשד, לא הפרה.
        הסקריפט אינו מבין סמנטיקה, ולכן הוא מסמן ולא פוסל.
        """
        new = list(ORIGINAL)
        new[0] = ("הערר שלפנינו עוסק בבקשה לשימוש חורג במקרקעין הידועים "
                  "כחלקה 42 בגוש 6789, וזאת לאחר שנשקלו כלל השיקולים הרלוונטיים "
                  "לרבות טענות הצדדים בעניין זה.")
        f = pc.check_all(build(ORIGINAL), new)
        self.assertIn(pc.status_of(f), ("עבר עם הערות", "נכשל"))
        self.assertTrue(any(x.check == "5-meaning" for x in f)
                        or any(x.check == "1-paragraphs" for x in f))

    def test_missing_operative_marker_warns(self):
        no_op = ORIGINAL[:4]
        f = pc.check_all(build(no_op), build(no_op))
        self.assertTrue(any(x.check == "4-operative" and x.severity == "ORANGE"
                            for x in f),
                        "היעדר חלק אופרטיבי חייב להיות אזהרה ולא שתיקה")


class TestNormalization(unittest.TestCase):
    def test_directional_marks_and_quote_styles_do_not_create_false_positives(self):
        """
        טקסט שעבר דרך Word עשוי לשאת RLM וגרשיים טיפוגרפיים. אם הנורמליזציה
        לא מטפלת בהם, כל פסקה תיראה כאילו השתנתה והדוח יטבע ברעש.
        """
        new = [p.replace('"', "”").replace(" ", " ‏", 1) for p in ORIGINAL]
        f = pc.check_all(build(ORIGINAL), new)
        self.assertNotEqual(pc.status_of(f), "נכשל",
                            [x.message for x in f])


if __name__ == "__main__":
    unittest.main(verbosity=2)
