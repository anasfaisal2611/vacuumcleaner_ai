import re

with open("schedule.txt", encoding="utf-8") as f:
    lines = f.read().splitlines()

precedences = re.findall(r"\(\s*(D\d+)\s*,\s*(D\d+)\s*\)", lines[2])
print(precedences)
latest=re.findall(r"\(\s*(D\d+)\s*,\s*(T\d+)\s*\)", lines[4])
print(latest)
domains=[f"T{i+1}" for i in range(int(lines[0]))]
print(domains)