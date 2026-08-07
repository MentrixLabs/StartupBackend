from sqlalchemy import insert, select

from db.db import async_session_maker


class BaseDAO:
    model = None

    @classmethod
    async def find_by_id(cls, model_id: int):
        async with async_session_maker() as session:
            try:
                query = select(cls.model).filter_by(id=model_id)
                result = await session.execute(query)
                return result.scalar_one_or_none()
            except Exception as error:
                print(error)
                return None

    @classmethod
    async def find_one_or_none(cls, **filter_by):
        async with async_session_maker() as session:
            try:
                query = select(cls.model).filter_by(**filter_by)
                result = await session.execute(query)
                return result.scalar_one_or_none()
            except Exception as error:
                print(error)
                return None

    @classmethod
    async def find_all(cls, **filter_by):
        async with async_session_maker() as session:
            try:
                query = select(cls.model).filter_by(**filter_by)
                result = await session.execute(query)
                return result.scalars().all()
            except Exception as error:
                    print(error)
                    return None

    @classmethod
    async def add(cls, **data):
        async with async_session_maker() as session:
            try:
                instance = cls.model(**data)
                session.add(instance)
                await session.commit()
                await session.refresh(instance)  # подгружаем все поля (id, created_at и т.д.)
                return instance
            except Exception as error:
                print(error)
                return None

    @classmethod
    async def delete(cls, **data):
        async with async_session_maker() as session:
            try:
                query = await session.execute(select(cls.model).filter_by(**data))
                result = query.scalars().first()
                if result:
                    await session.delete(result)
                    await session.commit()
                    return result
                return None
            except Exception as error:
                print(error)
                return None

    @classmethod
    async def update(cls, model_id: int, **data):
        async with async_session_maker() as session:
            try:
                query = await session.execute(select(cls.model).filter_by(id=model_id))
                result = query.scalars().first()
                if result:
                    for key, value in data.items():
                        setattr(result, key, value)
                    await session.commit()
                    return result
                return None
            except Exception as error:
                    print(error)
                    return None
