# Legal database reference (generic)

Knowledge about how the Legal case-management software (Access/Jet database `MasTmd.mdb` + a document folder tree) stores data, as verified on one installation by comparing the database before and after actions in the program itself. Use it to understand what the tool writes. Catalog numbers (kinds, case types, stages) come from the standard Legal catalogs; `ListKinds`, `ListStatuses`, `ListStages` show what your installation has.

## 1. Files and access
- Database `MasTmd.mdb` (Jet 4.0, password protected) -> needs **32-bit** Windows PowerShell; the tool relaunches itself in 32-bit. Documents live in `tmpDocs\<client name> <case number>\...`; deleted documents go to `DeletedFiles\`.
- The tool opens the database in shared mode, so it can run while Legal is open - but see the concurrency rule below.

## 2. Core tables
| table | content |
|---|---|
| `tblCustomer` | clients. `Pname` = family name, `Lname` = first name (companies: name in `Lname`) |
| `tblCase` | case: `CustomerID`, `CaseNum` (shown number), `CaseCustName` (first + family), `SueKind` (case type), `CaseStatus` (free text), `CaseCloseDate`, `NodeCaption` + `CurrentFlowID` (current stage). Sub-folders are cases with `SueKind=77` and `CaseParentID` |
| `tblCaseDetail`, `tblCaseValues` | one details row per case; 4 value rows (`nzSueTotal/Real/Outcome`, `nzRisk`) for tort cases |
| `tblCaseNodeFlow` | stage history: one row per entry into a stage |
| `tblCaseAct` | **every act**: documents, events, notes, calls, tasks, billing lines |
| `tblBasket` | calendar entries (one row per meeting / hearing / reminder) |
| `tblBankDeletes`, `tblBankOutlookBIN` | deletion log and Outlook-sync bin |
| `tblBankActKind`, `tblBankSueKind`, `tblBankStatusText`, `tblBizProducts` | catalogs: act kinds, case types, statuses, billing products |

## 3. Opening a case
Writes: a customer (unless existing), the case (number = highest + 1, `NodeCaption`, `CurrentFlowID`), a `tblCaseNodeFlow` row, a `tblCaseDetail` row, and for tort types 4 `tblCaseValues` rows. Types supported by the tool: 24 general (stage "general"), 22 general torts / 98 road-accident-injury / 20 national insurance / 102 work-related road accident (stage "open case" + value rows). The case folder is created on the first document import. A company name with quotes (e.g. Ltd.) is stored without quotes because quotes are illegal in folder names.

## 4. Documents
A document is one `tblCaseAct` row; its file is `<ActID><ActTeur>.<ext>` and the row stores the full path in `DocPath`. Rules the tool keeps: **file name = ActID + description (`ActTeur`)**, kind 1 = outgoing letter (sender = user), kind 2 = incoming letter (no sender).
- Add: act row first (to get the ActID), then the file, then `DocPath`.
- Rename: `ActTeur` + `DocPath` + file together (never the description alone).
- Move: `CaseID` (the target case or sub-folder) + `DocPath` + file.
- Sub-folder: a case row (`SueKind=77`, `CaseParentID`, `CaseSubject`/`CaseNumSort` = folder name); documents inside belong to the sub-folder case, path contains every level. Renaming a sub-folder updates the directory and every `DocPath` inside.
- Illegal file-name characters are replaced; a double quote becomes the Hebrew gershayim; titles are cut at 99 characters.
- `DocPath` values may carry an old prefix (e.g. `C:\Timin\tmpDocs`); the tool resolves them against the current Legal folder.

## 5. Calendar events
Common fields: kind, date, description, sender = user, receiver = client ("family first"), `ActDueDate`.
| kind | name | extra fields | basket row | colour (`ActColor`) |
|---|---|---|---|---|
| 14 | meeting | start/end, product "meeting", alarm 30 min before | yes | 7 green |
| 3 | pre-trial | start/end, product "hearing", no alarm | yes | 16 purple |
| 4 | hearing | start/end, alarm 30 min before | yes | 4 blue |
| 11 | reminder | start/end, no alarm | yes | 1 red |
| 7 | task | receiver = user, alarm 10 min before | no | - |
| 15 | phone call | product "phone call" | no | - |
| 39 / 66 | event / internal note | `FlowID` = case's current stage | no | - |
| 52 | damage assessment | amount + VAT | no | - |
No colour = turquoise. Other kinds in the court-hearing group use the hearing template, in the meeting group the meeting template (untested). The default location number comes from the settings. Billing product prices are defined per office in the program.

## 6. Deleting
Deleting a document or event in Legal: the act row is deleted for good; a `tblBankDeletes` row is added (type, description, date `dd/MM/yyyy`, sender, receiver); the file moves to `DeletedFiles\` with its name; for calendar kinds a `tblBankOutlookBIN` row is added; the `tblBasket` row stays. The tool does exactly this.

## 7. Status and closing
- Status = free text in `CaseStatus`, chosen from the catalog `tblBankStatusText` (9999 = "closed" is special). A status added to the catalog appears in Legal's status list.
- **Closing a case = status "closed" AND `CaseCloseDate` together. Any other status change does not touch the close date. A case is open when both are empty.**
- Hiding closed cases from the tree and search is a per-user program setting (`tblBankReg`, `HideCloseCaseInTreeSearchResults_<user>`), not stored in the case.

## 8. Stages (advanced, optional)
A process model per case type is a graph (`tblModels`, `tblNodes`, `tblNodeChilds`). Changing a case's stage in Legal inserts a `tblCaseNodeFlow` row and updates `CurrentFlowID` + `NodeCaption` (the date typed in the stage dialog is not stored). Most offices only ever use the opening stage.

## 9. Concurrency and limits
- If a case is open in a Legal card while the tool writes to it, Legal's next save of that card fails with "Row cannot be located for updating". Close and reopen the card (or avoid editing the same case in both).
- Not covered: invoices, payments, bookkeeping, enforcement (Hozaa LaPoal) modules, client personal data, process-model editing, automation rules.
