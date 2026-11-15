# דוח גישה ישירה - מיפוי השדות

מסמך עזר: מה נכנס לכל שדה בקובץ הנתונים. הנחיות העבודה עצמן נמצאות ב-SKILL.md.

השדות ממוינים לפי סדר הופעתם בטופס. סך הכול 57 שדות.

## רשימת השדות

### כותרת התיק

| שדה | תוכן |
|---|---|
| `cLegalAidNumber` | מס' תיק סיוע |
| `contactName` | שם הלקוח |

### החלטה על מתן סיוע משפטי

| שדה | תוכן |
|---|---|
| `appointmentDate` | מועד קבלת המינוי |
| `filingDeadline` | מועד אחרון להגשה |
| `chk_urgency_regular` / `chk_urgency_urgent` / `chk_urgency_emergency` | דחיפות ההליך: רגיל / דחוף / בהול |
| `chk_aid_appeal` | הגשת ערעור או נימוקי ערעור לבית הדין |
| `chk_aid_consulting` | יעוץ והדרכה |
| `chk_aid_additional_ni` | נדרש סיוע נוסף במיצוי זכויות בביטוח לאומי |
| `chk_aid_additional_other` | נדרש סיוע נוסף בתחום אחר |
| `chk_add_urgency_regular` / `chk_add_urgency_urgent` / `chk_add_urgency_emergency` | דחיפות ההליך הנוסף |
| `chk_aid_none` | אי מתן סיוע משפטי |

### דיווח לגבי קשר עם הלקוח

| שדה | תוכן |
|---|---|
| `contactDelayReason` | סיבת עיכוב ביצירת קשר |
| `firstContactDate` | תאריך יצירת קשר ראשוני |
| `meetingDate` | תאריך פגישה |
| `meetingDelayReason` | סיבת עיכוב בפגישה |
| `meetingAttendees` | נוכחים בפגישה |
| `chk_contact_ok` / `chk_contact_bad` | הקשר עם הלקוח תקין / לא תקין |
| `contactDetail` | פירוט לגבי הקשר |

### פרטי ההליך

| שדה | תוכן |
|---|---|
| `proceedingNumber` | מספר הליך |
| `courtName` | בית דין / בית משפט |
| `proceedingSubject` | עניין ההליך |
| `claimSummary` | תמצית התביעה/הערעור |
| `defenseClaims` | פירוט קצר של טענות ההגנה, ככל שהוגשו |

### בחינת הסיכוי המשפטי

תיבות פירוט בלבד, ללא כן/לא. התשובה משתקפת בניסוח הפירוט עצמו.

**נכות כללית, נכות מעבודה, נכות איבה, ניידות**

| שדה | השאלה |
|---|---|
| `q1DocsDetail` | האם הוועדה התייחסה לכל המסמכים הרפואיים? אילו מסמכים לא נבחנו |
| `q2ReasonDetail` | האם ההחלטה מנומקת וניתן להתחקות אחר הלך הרוח של הוועדה? מהי ההנמקה החסרה |
| `q4PanelComposition` | האם הרכב הוועדה תואם? מה היה ההרכב |
| `q6ComplaintsDetail` | האם התייחסו לכל תלונות הלקוח |
| `q8ClinicalGap` | האם נערכה בדיקה קלינית, והאם יש פער בינה לבין המסמכים שהוגשו |

**נכות - אי כושר**

| שדה | השאלה |
|---|---|
| `q9MoharaDetail` | ביטוי להלכת מוהרה: גיל, רקע תעסוקתי, השכלה. אילו נתונים חסרים |
| `q10RehabDetail` | פער בין החלטת פקיד השיקום לוועדה, ומהות הפער |

**שירותים מיוחדים / סיעוד**

| שדה | השאלה |
|---|---|
| `q11ScoreDetail` | פער בין הניקוד שניתן למצב הלקוח, ומהות הפער |
| `q12UniqueDetail` | היבטים ייחודיים: נפילות, מצב קוגניטיבי, צורך בהשגחה |

### המלצה / הודעה אחרת

| שדה | תוכן |
|---|---|
| `chk_rec_consulting` | ניתן ייעוץ והדרכה חלף ייצוג |
| `chk_rec_waiver` | הלקוח ויתר על הסיוע המשפטי |
| `chk_rec_replacement` | מתבקשת החלפת ייצוג |
| `chk_rec_no_contact` | לא נוצר קשר |
| `chk_rec_no_meeting` | לא התקיימה פגישה |
| `chk_rec_undecided` | עדיין לא ניתן לקבל החלטה |
| `chk_rec_docs_needed` | נדרשים מסמכים או מידע נוסף |
| `chk_rec_refusal` | המלצה לסירוב, אין סיכוי משפטי |
| `recommendationDetail` | פירוט ההמלצה |

### מיצוי זכויות

| שדה | תוכן |
|---|---|
| `chk_no_additional` | לא נחוץ סיוע משפטי בנושאים נוספים |
| `chk_additional_ni` | נחוץ סיוע בתחום הביטוח הלאומי שאינו כלול במינוי |
| `additionalAidNIDetail` | פירוט |
| `chk_additional_other` | נחוץ סיוע משפטי בנושאים נוספים |
| `additionalAidOtherDetail` | פירוט |
| `chk_add_aid_regular` / `chk_add_aid_urgent` / `chk_add_aid_emergency` | דחיפות הסיוע הנוסף |
| `additionalAidDeadlines` | מועדים |
| `chk_willing_to_represent` | הסיוע בתחום התמחותי ומעוניין לייצג |
| `notes` | הערות |
