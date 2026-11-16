"""Optional CI-injected Groq credential, empty in the public source tree.

Never commit a real key here. CI overwrites this module from a private Secret
on the trusted main release workflow; packaged binaries can expose the key.
"""
BUILTIN_GROQ_KEY = ""
