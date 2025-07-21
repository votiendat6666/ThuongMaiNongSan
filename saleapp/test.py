import json

# Đọc dữ liệu từ file
with open("data/products.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Ghi lại với định dạng đặc biệt
with open("data/products.json", "w", encoding="utf-8") as f:
    f.write('[\n')
    for i, obj in enumerate(data):
        # Nếu có extra_info và có order thì xử lý riêng
        if "extra_info" in obj and "order" in obj["extra_info"]:
            extra = obj["extra_info"]
            order_line = json.dumps(extra["order"], ensure_ascii=False, separators=(", ", ": "))

            # Xoá 'order' để ghi sau cùng
            del extra["order"]

            # Ghi object ra dòng
            f.write('  {\n')
            for j, (k, v) in enumerate(obj.items()):
                if k == "extra_info":
                    f.write(f'    "{k}": {{\n')
                    f.write(f'      "order": {order_line},\n')
                    for idx, (kk, vv) in enumerate(extra.items()):
                        comma = "," if idx < len(extra) - 1 else ""
                        vv_json = json.dumps(vv, ensure_ascii=False)
                        f.write(f'      "{kk}": {vv_json}{comma}\n')
                    f.write('    }\n')
                else:
                    v_json = json.dumps(v, ensure_ascii=False)
                    f.write(f'    "{k}": {v_json},\n')
            f.write('  }')
        else:
            # Object không có extra_info đặc biệt
            line = json.dumps(obj, ensure_ascii=False, indent=4)
            f.write(f'{line}')

        f.write(',\n' if i < len(data) - 1 else '\n')
    f.write(']')





