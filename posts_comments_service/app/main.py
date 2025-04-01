from .handlers import serve

print("name", __name__)
if __name__ == '__main__':
    print("main")
    serve()