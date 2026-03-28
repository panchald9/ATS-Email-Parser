from affinda import AffindaAPI, TokenCredential

api_key = "aff_51af6d8a766dfb1cab2d861e6e2c5d896f86d6db"

credential = TokenCredential(token=api_key)
client = AffindaAPI(credential=credential)

with open("2.pdf", "rb") as f:
    resume = client.create_document(file=f)

print(resume.as_dict())