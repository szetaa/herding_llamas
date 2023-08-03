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
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

import uuid


Base = declarative_base()


class Inference(Base):
    __tablename__ = "inference"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    node_key = Column(String(255))
    prompt_key = Column(String(255))
    prompt_version = Column(String(5))
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
        print(id, inference_data)
        session = self.Session()
        inference = session.query(Inference).filter(Inference.id == id).first()
        if not inference:
            raise ValueError(f"Inference with id {id} not found")

        for key, value in inference_data.items():
            if hasattr(inference, key):
                setattr(inference, key, value)

        session.commit()

    def get_node_statistics(self, hours=24):
        session = self.Session()

        twenty_four_hours_ago = text(f"(datetime('now', '-{hours} hours'))")

        results = (
            session.query(
                Inference.node_key,
                (
                    cast(
                        func.strftime("%Y-%m-%d %H:00:00", Inference.created_ts), String
                    )
                ).label("hour"),
                func.count(Inference.id).label("record_count"),
                func.avg(Inference.input_tokens).label("average_input_tokens"),
                func.sum(Inference.input_tokens).label("sum_input_tokens"),
                func.avg(Inference.output_tokens).label("average_output_tokens"),
                func.sum(Inference.output_tokens).label("sum_output_tokens"),
                func.avg(Inference.elapsed_seconds).label("average_elapsed_seconds"),
                func.sum(Inference.elapsed_seconds).label("sum_elapsed_seconds"),
            )
            .filter(Inference.created_ts >= twenty_four_hours_ago)
            .group_by(Inference.node_key, "hour")
            .order_by(Inference.node_key, "hour")
            .all()
        )

        data = {}
        hours_in_seconds = 60 * 60 * hours

        for row in results:
            data[row[0]] = {
                "node_key": row[0],
                "hour": row[1],
                "record_count": row[2],
                "average_input_tokens": row[3],
                "sum_input_tokens": row[4],
                "average_output_tokens": row[5],
                "sum_output_tokens": row[6],
                "average_elapsed_seconds": round(row[7], 2),
                "sum_elapsed_seconds": round(row[8], 2),
                "pct_used_seconds": (row[8] / (hours_in_seconds)) * 100,
                "pct_unused_seconds": (1 - row[8] / (hours_in_seconds)) * 100,
            }

        return data
