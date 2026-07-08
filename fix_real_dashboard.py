import os

target = 'blogs/views.py'
with open(target, 'r', encoding='utf-8') as f:
    text = f.read()

old_logic = """        total_images = 0

        for blog in recent_blogs:

            total_images += 2      # hero + conclusion

            total_images += (
                blog.chapters.count()
            )"""

new_logic = """        from django.db.models import Count
        chapter_count = blogs.aggregate(tc=Count('chapters'))['tc'] or 0
        total_images = (total_blogs * 2) + chapter_count"""

text = text.replace(old_logic, new_logic)

with open(target, 'w', encoding='utf-8') as f:
    f.write(text)

print("Real dashboard view fixed")
