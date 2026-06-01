"""
seed_products.py
Management command: python manage.py seed_products

Inserts the initial product catalog into the ShopProduct table.
Safe to run multiple times — uses get_or_create so existing rows are skipped.

Run this once after the first migration on a fresh database, or include it
in the Render build command so every new deployment starts with products.
"""

from django.core.management.base import BaseCommand
from store.models import ShopProduct


# Full product list matching the hardcoded items in shop.js.
# Keeping them in sync means the shop page shows consistent data whether
# products come from the JS fallback or the database.
PRODUCTS = [
    {
        'product_name': 'Reusable Water Bottle',
        'desc':  'Lightweight bottle to keep you hydrated while gardening or on the go.',
        'price': 18.00,
        'src':   'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400',
    },
    {
        'product_name': 'Cotton Tote Bag',
        'desc':  'Durable everyday tote for groceries, tools, and market finds.',
        'price': 14.00,
        'src':   'https://images.unsplash.com/photo-1585914924626-15adac1e6402?w=400',
    },
    {
        'product_name': 'Steel Straw Set',
        'desc':  'Reusable stainless steel straws with a cleaner, perfect for daily use.',
        'price': 9.00,
        'src':   'https://images.unsplash.com/photo-1613478223719-2ab802602423?w=400',
    },
    {
        'product_name': 'Succulents',
        'desc':  'Low-maintenance mini succulents to brighten desks and windowsills.',
        'price': 12.00,
        'src':   'https://images.unsplash.com/photo-1459411552884-841db9b3cc2a?w=400',
    },
    {
        'product_name': 'Flower Seeds',
        'desc':  'Assorted seasonal flower seeds for colorful blooms all season long.',
        'price': 6.00,
        'src':   'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=400',
    },
    {
        'product_name': 'Aloe Vera',
        'desc':  'Known for its soothing gel that helps treat burns and skin irritation. Easy to grow and requires little water.',
        'price': 12.67,
        'src':   'https://www.stockvault.net/data/2021/01/03/282191/preview16.jpg',
    },
    {
        'product_name': 'Snake Plant',
        'desc':  'A hardy houseplant that survives in low light with minimal watering. Helps improve indoor air quality.',
        'price': 12.99,
        'src':   'https://cdn.shopify.com/s/files/1/0619/1218/7051/files/1661954674-dsc-7058-1.jpg',
    },
    {
        'product_name': 'Peace Lily',
        'desc':  'Known for its elegant white blooms. Thrives indoors and helps filter certain pollutants from the air.',
        'price': 15.96,
        'src':   'https://www.meadowsfarms.com/great-big-greenhouse-gardening-blog/wp-content/uploads/sites/2/2025/03/bonnie-blog-peace-lily.jpg.webp',
    },
    {
        'product_name': 'Lavender',
        'desc':  'Known for its fragrant purple flowers and use in aromatherapy. Promotes relaxation and reduces stress.',
        'price': 11.96,
        'src':   'https://www.provenwinners.com/sites/provenwinners.com/files/imagecache/low-resolution/ifa_upload/lavandula_summer_serenade_apj25_3.jpg',
    },
    {
        'product_name': 'Basil',
        'desc':  'A popular culinary herb used in Mediterranean dishes. Growing basil at home promotes sustainable cooking.',
        'price': 11.96,
        'src':   'https://aanmc.org/wp-content/uploads/2021/08/987-1024x681.jpg',
    },
    {
        'product_name': 'Mint',
        'desc':  'A fast-growing herb known for its refreshing flavor. Commonly used in teas, desserts, and beverages.',
        'price': 11.76,
        'src':   'https://media.post.rvohealth.io/wp-content/uploads/sites/3/2025/06/mint-good-GettyImages-2216675819-Header-1024x575.jpg',
    },
    {
        'product_name': 'Rosemary',
        'desc':  'A fragrant herb widely used in cooking. Grows well in sunny conditions and requires very little water.',
        'price': 8.49,
        'src':   'https://lancaster.unl.edu/sites/unl.edu.ianr.extension.lancaster/files/2024-12/rosemary-gb8cd2e20e_1920.jpg',
    },
    {
        'product_name': 'Monstera',
        'desc':  'A tropical plant known for its large split leaves. Widely used as a decorative indoor plant.',
        'price': 25.76,
        'src':   'https://cdn.mos.cms.futurecdn.net/w5g9MUrhQ8nRgAhRamAKvX.jpg',
    },
    {
        'product_name': 'Spider Plant',
        'desc':  'A resilient houseplant with long arching leaves. Easy to care for and produces small plantlets.',
        'price': 20.06,
        'src':   'https://cdn.mos.cms.futurecdn.net/Rw63sJPwqukKneBYZkpjUn.jpg',
    },
    {
        'product_name': 'Chamomile',
        'desc':  'A flowering herb commonly used to make calming herbal tea. Known for its relaxing effects.',
        'price': 9.50,
        'src':   'https://cdn.mos.cms.futurecdn.net/v2sQs7MsmECNVGZBqXtwkH.jpg',
    },
    {
        'product_name': 'Sunflower',
        'desc':  'A bright plant that supports pollinators like bees. Seeds are used in food and cooking oil.',
        'price': 22.55,
        'src':   'https://www.lunafloral.my/cdn/shop/articles/pexels-pixabay-54267.jpg?v=1724733421&width=2048',
    },
]


class Command(BaseCommand):
    help = 'Seed the database with the initial product catalog.'

    def handle(self, *args, **kwargs):
        created = 0
        skipped = 0

        for p in PRODUCTS:
            _, was_created = ShopProduct.objects.get_or_create(
                product_name=p['product_name'],
                defaults={
                    'desc':  p['desc'],
                    'price': p['price'],
                    'src':   p['src'],
                }
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Done — {created} products added, {skipped} already existed.'
            )
        )
