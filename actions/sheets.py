from googleapiclient.discovery import build


class SheetsActions:
    def __init__(self, creds):
        self.sheets_service = build("sheets", "v4", credentials=creds)
        self.drive_service = build("drive", "v3", credentials=creds)

    def create_spreadsheet(self, title: str) -> str:
        spreadsheet = {"properties": {"title": title}}
        result = (
            self.sheets_service.spreadsheets()
            .create(body=spreadsheet, fields="spreadsheetId,spreadsheetUrl")
            .execute()
        )
        return (
            f"✅ スプレッドシート作成: {title}\n"
            f"ID: {result['spreadsheetId']}\n"
            f"URL: {result['spreadsheetUrl']}"
        )

    def read_sheet(self, spreadsheet_id: str, range_: str = "Sheet1") -> str:
        result = (
            self.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_)
            .execute()
        )
        values = result.get("values", [])
        if not values:
            return "データがありません"
        lines = []
        for row in values:
            lines.append("\t".join(str(c) for c in row))
        return "\n".join(lines)

    def write_sheet(self, spreadsheet_id: str, range_: str, values: list) -> str:
        body = {"values": values}
        result = (
            self.sheets_service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_,
                valueInputOption="USER_ENTERED",
                body=body,
            )
            .execute()
        )
        return f"✅ 書き込み完了: {result.get('updatedCells', 0)}セル更新"

    def append_sheet(self, spreadsheet_id: str, range_: str, values: list) -> str:
        body = {"values": values}
        result = (
            self.sheets_service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_,
                valueInputOption="USER_ENTERED",
                body=body,
            )
            .execute()
        )
        return f"✅ 追記完了: {result['updates'].get('updatedCells', 0)}セル追加"

    def list_sheets(self, spreadsheet_id: str) -> str:
        result = (
            self.sheets_service.spreadsheets()
            .get(spreadsheetId=spreadsheet_id)
            .execute()
        )
        sheets = result.get("sheets", [])
        lines = [f"📊 {s['properties']['title']} (ID: {s['properties']['sheetId']})" for s in sheets]
        return "\n".join(lines) if lines else "シートがありません"

    def add_sheet(self, spreadsheet_id: str, sheet_name: str) -> str:
        body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        self.sheets_service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
        return f"✅ シート追加: {sheet_name}"
