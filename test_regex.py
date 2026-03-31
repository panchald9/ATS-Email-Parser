import re

value = 'Pilog India Pvt Ltd, Hyderabad, India August 2007 to September 2009'

# Test pattern 1
p1 = r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|september|october|november|december)[.,\-\s]+\d{4}'
m1 = re.search(p1, value, re.I)
print('Pattern 1 match:', bool(m1), 'match:', m1.group() if m1 else 'None')

# Test pattern 2
p2 = r'\d{4}\s*(?:to|–|-|:)\s*(?:\d{4}|present|till)'
m2 = re.search(p2, value, re.I)
print('Pattern 2 match:', bool(m2), 'match:', m2.group() if m2 else 'None')

# What about with "present"?
val2 = 'Some address with dates 2020 - present'
m3 = re.search(p2, val2, re.I)
print('Pattern 2 on dates with present:', bool(m3), 'match:', m3.group() if m3 else 'None')
