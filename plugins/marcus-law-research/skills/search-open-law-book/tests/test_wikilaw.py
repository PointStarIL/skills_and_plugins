#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
בדיקות ל-wikilaw.py.

הרצה מקומית (ללא רשת):
    python3 tests/test_wikilaw.py

הרצה כולל בדיקות רשת מול ויקיטקסט:
    WIKILAW_ONLINE=1 python3 tests/test_wikilaw.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import wikilaw  # noqa: E402

ONLINE = os.environ.get("WIKILAW_ONLINE") == "1"

# מקטע אמיתי ממבנה ספר החוקים הפתוח, מקוצר לצורך הבדיקה
FIXTURE = """{{ח:קטע2|פרק ט|פרק ט׳: ביטוח נכות}}
{{ח:קטע3|פרק ט סימן ד|סימן ד׳: קביעת נכות ואי־כושר}}

{{ח:סעיף|208|אחוזי נכות רפואית|תיקון: תשס״ח־10}}
{{ח:תת|(א)}} תנאי לקביעת אי־כושר להשתכר הוא שנקבעה למבוטח נכות רפואית.
{{ח:תת|(ב)}} הוראות {{ח:פנימי|סעיף 209|סעיף 209}} יחולו.

{{ח:סעיף|209|דרגת אי־כושר להשתכר|תיקון: תשע״ז־6}}
{{ח:תת|(א)}} פקיד תביעות יחליט אם התובע הינו נכה.
{{ח:תתת|(1)}} '''לענין זה''' יראו את המבוטח כנכה.
{{ח:ת}} {{ח:הערה|(פקע)}}

{{ח:קטע3|פרק ט סימן ה|סימן ה׳: שונות}}
{{ח:סעיף|210|ביטול|תיקון: תש״ף}}
{{ח:ת}} בוטל.
"""


class TestRender(unittest.TestCase):
    """הכלל המרכזי: הרינדור מסיר תבניות עיצוב אך אינו משנה מילים."""

    def test_internal_link_keeps_display_text(self):
        self.assertEqual(wikilaw.render("{{ח:פנימי|סעיף 104|סעיף 104(א)}}"), "סעיף 104(א)")

    def test_external_link_keeps_display_text(self):
        out = wikilaw.render("{{ח:חיצוני|פקודת מס הכנסה#סעיף 32|בסעיף 32 בפקודת מס הכנסה}}")
        self.assertEqual(out, "בסעיף 32 בפקודת מס הכנסה")

    def test_note_wrapped_once(self):
        self.assertEqual(wikilaw.render("{{ח:הערה|(פקע)}}"), "(פקע)")
        self.assertEqual(wikilaw.render("{{ח:הערה|בוטל}}"), "(בוטל)")

    def test_nested_templates(self):
        out = wikilaw.render("{{ח:קטע4||{{ח:הערה|({{ח:פנימי|סעיף 1|סעיף 1}})}}}}")
        self.assertEqual(out, "(סעיף 1)")

    def test_bold_italic_stripped(self):
        self.assertEqual(wikilaw.render("'''מודגש''' ו''נטוי''"), "מודגש ונטוי")

    def test_subsection_markers(self):
        self.assertIn("(א)", wikilaw.render("{{ח:תת|(א)}} טקסט"))
        self.assertIn("(1)", wikilaw.render("{{ח:תתת|(1)}} טקסט"))

    def test_two_markers_on_one_template(self):
        """{{ח:תת|(ד)|(1)}} — שני הסמנים חייבים להופיע בפלט."""
        out = wikilaw.render("{{ח:תת|(ד)|(1)}} טקסט")
        self.assertIn("(ד)", out)
        self.assertIn("(1)", out)
        out = wikilaw.render("{{ח:תתת|(4)|(א)}} טקסט")
        self.assertIn("(4)", out)
        self.assertIn("(א)", out)

    def test_structural_templates_dropped(self):
        for t in ("{{ח:התחלה}}", "{{ח:סוף}}", "{{ח:מפריד}}", "{{ח:סוגר}}"):
            self.assertEqual(wikilaw.render(t), "")

    def test_words_are_not_altered(self):
        out = wikilaw.render("{{ח:תת|(א)}} תנאי לקביעת אי־כושר להשתכר הוא שנקבעה נכות רפואית.")
        self.assertIn("תנאי לקביעת אי־כושר להשתכר הוא שנקבעה נכות רפואית.", out)
        self.assertIn("־", out)  # המקף העברי של הנוסח המקורי נשמר


class TestSplitArgs(unittest.TestCase):
    def test_top_level_only(self):
        self.assertEqual(wikilaw._split_args("ח:סעיף|118|כותרת"), ["ח:סעיף", "118", "כותרת"])

    def test_pipe_inside_nested_template_is_not_a_separator(self):
        parts = wikilaw._split_args("ח:סעיף|1|{{ח:פנימי|א|ב}}")
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[2], "{{ח:פנימי|א|ב}}")


class TestStructure(unittest.TestCase):
    def setUp(self):
        self.blocks = wikilaw.parse_structure(FIXTURE)
        self.sections = [b for b in self.blocks if b["kind"] == "section"]
        self.headings = [b for b in self.blocks if b["kind"] == "heading"]

    def test_all_sections_found(self):
        self.assertEqual([b["num"] for b in self.sections], ["208", "209", "210"])

    def test_section_title_and_amendment(self):
        s = self.sections[1]
        self.assertEqual(s["title"], "דרגת אי־כושר להשתכר")
        self.assertEqual(s["amend"], "תיקון: תשע״ז־6")

    def test_heading_levels(self):
        self.assertEqual([h["level"] for h in self.headings], [2, 3, 3])
        self.assertEqual(self.headings[0]["title"], "פרק ט׳: ביטוח נכות")

    def test_section_body_stops_at_next_section(self):
        body = wikilaw.render(self.sections[0]["wikitext"])
        self.assertIn("תנאי לקביעת אי־כושר להשתכר", body)
        self.assertNotIn("פקיד תביעות יחליט", body)

    def test_context_chain(self):
        ctx = wikilaw._context(self.blocks, self.sections[1])
        self.assertEqual(ctx, ["פרק ט׳: ביטוח נכות", "סימן ד׳: קביעת נכות ואי־כושר"])

    def test_context_resets_on_new_sign(self):
        ctx = wikilaw._context(self.blocks, self.sections[2])
        self.assertEqual(ctx, ["פרק ט׳: ביטוח נכות", "סימן ה׳: שונות"])


class TestNormNum(unittest.TestCase):
    def test_trailing_dot_and_space(self):
        self.assertEqual(wikilaw.norm_num(" 118. "), "118")

    def test_hebrew_quote_marks_normalised(self):
        self.assertEqual(wikilaw.norm_num("127כב"), "127כב")
        self.assertEqual(wikilaw.norm_num("ג׳"), "ג'")

    def test_none_is_safe(self):
        self.assertEqual(wikilaw.norm_num(None), "")


@unittest.skipUnless(ONLINE, "בדיקות רשת: הפעל עם WIKILAW_ONLINE=1")
class TestLive(unittest.TestCase):
    """בדיקות חיות מול ויקיטקסט. עלולות להיכשל בשל הגבלת קצב של ויקימדיה."""

    def test_search_returns_the_law_page(self):
        d = wikilaw.api(action="query", list="search",
                        srsearch="חוק הביטוח הלאומי", srlimit=5, srnamespace=0)
        titles = [r["title"] for r in d["query"]["search"]]
        self.assertIn("חוק הביטוח הלאומי", titles)

    def test_fetch_page_has_metadata(self):
        pg = wikilaw.fetch_page("חוק בית הדין לעבודה")
        for k in ("wikitext", "revid", "timestamp", "url"):
            self.assertTrue(pg.get(k), "שדה חסר: %s" % k)
        self.assertIn("{{ח:", pg["wikitext"])

    def test_known_section_text(self):
        pg = wikilaw.fetch_page("חוק בית הדין לעבודה")
        blocks = wikilaw.parse_structure(pg["wikitext"])
        hit = [b for b in blocks if b["kind"] == "section" and wikilaw.norm_num(b["num"]) == "33"]
        self.assertEqual(len(hit), 1)
        self.assertIn("בדרך הנראית לו טובה ביותר לעשיית משפט צדק",
                      wikilaw.render(hit[0]["wikitext"]))

    def test_source_line_has_link_and_date(self):
        pg = wikilaw.fetch_page("חוק בית הדין לעבודה")
        line = wikilaw.source_line(pg, "סעיף 33")
        self.assertIn("he.wikisource.org", line)
        self.assertIn("revid", line)


if __name__ == "__main__":
    unittest.main(verbosity=2)
