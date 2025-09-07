from models import mapper_registry
from database import engine

def create_tables():
    mapper_registry.metadata.create_all(engine)

if __name__ == '__main__':
    create_tables()
