import os

# 1. Update HTML
target = 'blogs/templates/blogs/my_blogs.html'
with open(target, 'r', encoding='utf-8') as f:
    html = f.read()

# Add onchange to selects
html = html.replace('name="category"', 'name="category"\n                onchange="this.form.submit()"')
html = html.replace('name="sort"', 'name="sort"\n                onchange="this.form.submit()"')

with open(target, 'w', encoding='utf-8') as f:
    f.write(html)


# 2. Update views.py for robust categories
views_target = 'blogs/views.py'
with open(views_target, 'r', encoding='utf-8') as f:
    views_code = f.read()

old_cat_logic = """    categories = Blog.objects.filter(

        is_deleted=False,

    ).order_by("category").values_list(

        "category",

        flat=True,

    ).distinct()"""

new_cat_logic = """    raw_categories = Blog.objects.filter(is_deleted=False).values_list("category", flat=True)
    categories = sorted(list(set(c.strip() for c in raw_categories if c and c.strip())))"""

views_code = views_code.replace(old_cat_logic, new_cat_logic)

with open(views_target, 'w', encoding='utf-8') as f:
    f.write(views_code)

print("done")
