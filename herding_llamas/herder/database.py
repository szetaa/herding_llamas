from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    func,
    desc,
    cast,
    text,
)
from sqlalchemy.sql.functions import coalesce
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime, timedelta, timezone


import uuid


Base = declarative_base()


class Inference(Base):
    __tablename__ = "inference"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    node_key = Column(String(255))
    prompt_key = Column(String(255))
    prompt_version = Column(String(5))
    user_key = Column(String(50))
    raw_input = Column(Text)
    infer_input = Column(Text)
    response = Column(Text)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    elapsed_seconds = Column(Float)
    session_id = Column(String(255))
    score = Column(Integer)  # between 1-5
    feedback = Column(Text)
    created_ts = Column(DateTime, default=func.now())
    updated_ts = Column(DateTime, onupdate=func.now())


class Database:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    # inference CRUD operation
    def list_inference(self):
        session = self.Session()
        inference = (
            session.query(Inference)
            .order_by(desc(Inference.created_ts))
            .limit(50)
            .all()
        )
        return inference

    def create_inference(self, inference_data):
        session = self.Session()
        inference = Inference(**inference_data)
        session.add(inference)
        session.commit()
        return inference.id

    def update_inference(self, id, inference_data):
        session = self.Session()
        inference = session.query(Inference).filter(Inference.id == id).first()
        if not inference:
            raise ValueError(f"Inference with id {id} not found")

        for key, value in inference_data.items():
            if hasattr(inference, key):
                setattr(inference, key, value)

        session.commit()

    def get_user_statistics(self, user_key, hours):
        session = self.Session()
        n_hours_ago = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = (
            session.query(
                func.count(Inference.id).label("request_count"),
                coalesce(func.sum(Inference.input_tokens), 0).label("sum_input_tokens"),
                coalesce(func.sum(Inference.output_tokens), 0).label(
                    "sum_output_tokens"
                ),
                coalesce(func.sum(Inference.elapsed_seconds), 0).label(
                    "sum_elapsed_seconds"
                ),
            )
            .filter(Inference.user_key == user_key, Inference.created_ts >= n_hours_ago)
            .first()
        )
        result = result._asdict()
        result["request"] = result["request_count"]
        result["token"] = result["sum_input_tokens"] + result["sum_output_tokens"]

        return result

    def get_node_statistics(self, hours=24):
        session = self.Session()

        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=hours)

        results = (
            session.query(
                Inference.node_key,
                func.count(Inference.id).label("record_count"),
                func.avg(Inference.input_tokens).label("average_input_tokens"),
                func.sum(Inference.input_tokens).label("sum_input_tokens"),
                func.avg(Inference.output_tokens).label("average_output_tokens"),
                func.sum(Inference.output_tokens).label("sum_output_tokens"),
                func.avg(Inference.elapsed_seconds).label("average_elapsed_seconds"),
                func.sum(Inference.elapsed_seconds).label("sum_elapsed_seconds"),
            )
            .filter(Inference.created_ts >= twenty_four_hours_ago)
            .group_by(Inference.node_key)
            .order_by(Inference.node_key)
            .all()
        )

        results = [row._asdict() for row in results]

        data = {}
        hours_in_seconds = 60 * 60 * hours

        for row in results:
            node_key = row["node_key"]
            data[node_key] = {
                "node_key": node_key,
                "record_count": row["record_count"],
                "average_input_tokens": row["average_input_tokens"],
                "sum_input_tokens": row["sum_input_tokens"],
                "average_output_tokens": row["average_output_tokens"],
                "sum_output_tokens": row["sum_output_tokens"],
                "average_elapsed_seconds": round(row["average_elapsed_seconds"], 2),
                "sum_elapsed_seconds": round(row["sum_elapsed_seconds"], 2),
                "pct_used_seconds": (row["sum_elapsed_seconds"] / (hours_in_seconds))
                * 100,
                "pct_unused_seconds": (
                    1 - row["sum_elapsed_seconds"] / (hours_in_seconds)
                )
                * 100,
            }

        return data
