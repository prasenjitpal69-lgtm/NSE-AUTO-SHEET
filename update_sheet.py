# ===========================
# Update Final list sheet
# ===========================

try:
    final_sheet = client.open_by_key(spreadsheet_id).worksheet("Final list")

    final_sheet.batch_clear(["A2:H1000"])

    rows = []

    for row in data_to_insert:
        rows.append([
            row[0],   # NSE CODE
            row[2],   # CMP
            row[1],   # VOLUME
            "",
            "",
            "",
            "",
            ""
        ])

    print("Rows =", len(rows))

    if rows:
        final_sheet.update(
            range_name="A2",
            values=rows
        )
        print("Final List Updated Successfully")
    else:
        print("No rows found")

except Exception as e:
    print("Final List Error:")
    print(str(e))
