# patch_spec.py — run on Windows CI to switch icon from .png to .ico
with open("studyquest.spec", "r") as f:
    content = f.read()
content = content.replace("icon='icon_256.png'", "icon='icon.ico'")
with open("studyquest.spec", "w") as f:
    f.write(content)
print("Spec patched: icon set to icon.ico")
