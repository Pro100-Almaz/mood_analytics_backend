from celery_worker import process_posts, fetch_comments_for_posts

keywords = ["водоснабжение", "субсидии", "водный кодекс", "ЗРК 411-VI", "питьевая вода", "разграничение полномочий",
           "центральные органы", "местные органы"]

posts = process_posts(keywords)
comments_data = fetch_comments_for_posts(posts)

print(comments_data)

# response['facebook'] = comments_data