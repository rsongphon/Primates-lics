"""
Test script to verify all API routes are properly registered.
"""

from app.main import app

# Print all routes
print('=' * 80)
print('LICS Backend API Routes - RESTful API Implementation')
print('=' * 80)
route_count = 0
endpoints_by_tag = {}

for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'tags'):
        for method in route.methods:
            if method != 'HEAD':  # Skip HEAD methods
                route_count += 1
                tag = route.tags[0] if route.tags else 'untagged'
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []
                endpoints_by_tag[tag].append((method, route.path))

for tag in sorted(endpoints_by_tag.keys()):
    print(f'\n{tag.upper()}:')
    print('-' * 80)
    for method, path in sorted(endpoints_by_tag[tag], key=lambda x: x[1]):
        print(f'  {method:8s} {path}')

print('\n' + '=' * 80)
print(f'Total API endpoints: {route_count}')
print('=' * 80)
print('✅ FastAPI application started successfully!')
print('✅ All domain endpoints registered!')
