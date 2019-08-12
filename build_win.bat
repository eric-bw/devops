pyinstaller migration_assistant.py --add-data "packagebuilder/wsdl/metadata-45.wsdl.xml;packagebuilder/wsdl" --onefile
mv dist\migration_assistant.exe .
git add migration_assistant.exe
git commit -m "build snapshot"
git push origin