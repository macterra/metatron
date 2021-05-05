import redis

r = redis.Redis(host='localhost', port=6379, db=0)

keys = r.keys("scanner/*")
keys.sort()

for key in keys:
    print(f"{key.decode():20} {r.get(key).decode()}")
