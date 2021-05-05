import redis

r = redis.Redis(host='localhost', port=6379, db=0)

foo = r.get("foo")
print(foo)

r.set("foobar", 666)
foobar = r.get("foobar")
print(int(foobar))

