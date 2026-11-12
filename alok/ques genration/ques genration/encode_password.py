import urllib.parse

raw_password = input("Apna Supabase DB Password yahan paste karein: ")
encoded_password = urllib.parse.quote_plus(raw_password)
print("\n✅ Encoded Password (isko connection string me use karein):")
print(encoded_password)