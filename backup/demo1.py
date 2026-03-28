from pyresparser import ResumeParser
import json
data = ResumeParser("1.pdf").get_extracted_data()

print(json.dumps(data, indent=8))