import re
content = open('address.txt', 'r', encoding='utf-16').read()
match = re.search(r'NEW_CONTRACT_ADDRESS: (0x[a-fA-F0-9]{40})', content)
if match:
    # write to a new clean file with utf-8 encoding
    with open('final_address.txt', 'w', encoding='utf-8') as f:
        f.write(match.group(1))
    print("Found address")
else:
    print("Not found")
