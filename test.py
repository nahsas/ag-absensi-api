test = "Muhammad Farrel Arrahman"
urutan = 5342
split_string = test.split(" ")
initital = ""
for text in split_string:
    initital += text[0].upper()
print(f"{initital}{str(urutan).zfill(5)}")