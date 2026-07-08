import os

target = 'blogs/templates/blogs/my_blogs.html'

with open(target, 'r', encoding='utf-8') as f:
    html = f.read()

# Replace options
options = [
    ('-created_at', 'Newest First'),
    ('created_at', 'Oldest First'),
    ('-updated_at', 'Recently Updated'),
    ('title', 'A &rarr; Z'),
    ('title', 'A → Z'),
]

for val, label in options:
    old_opt = f'<option value="{val}">'
    new_opt = f'<option value="{val}" {{% if selected_sort == "{val}" %}}selected{{% endif %}}>'
    html = html.replace(old_opt, new_opt)

with open(target, 'w', encoding='utf-8') as f:
    f.write(html)
    
print("Options fixed")
