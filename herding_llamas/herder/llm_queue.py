import asyncio
import uuid


# TaskQueue definition
class TaskQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.new_task_event = asyncio.Event()
        self.results = {}  # To store results of completed tasks
        self.result_events = {}  # To store events corresponding to each task

    async def enqueue_task(self, task_func, skill_required, allowed_workers=None):
        task_id = str(uuid.uuid4())
        self.result_events[task_id] = asyncio.Event()  # Create an event for this task
        await self.queue.put(
            (task_id, task_func, skill_required, allowed_workers or [])
        )
        self.new_task_event.set()
        return task_id

    async def try_dequeue_task(self, skills, worker_id):
        if self.queue.empty():
            return None, None
        task_id, task_func, skill_required, allowed_workers = await self.queue.get()
        if skill_required in skills and (
            not allowed_workers or worker_id in allowed_workers
        ):
            return task_id, task_func
        else:
            await self.queue.put((task_id, task_func, skill_required, allowed_workers))
            return None, None


# Worker definition
class Worker:
    def __init__(self, worker_id, task_queue, skills):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.skills = skills
        self.is_free = True

    async def start(self):
        try:
            while True:
                task_id, task_func = await self.task_queue.try_dequeue_task(
                    self.skills, self.worker_id
                )

                if not task_id:  # If no task matches the skills
                    await self.task_queue.new_task_event.wait()
                    self.task_queue.new_task_event.clear()
                    continue  # Go back and check the queue again

                self.is_free = False
                result = await task_func(
                    self.worker_id
                )  # Pass the worker_id to the task function
                self.task_queue.results[task_id] = result
                self.task_queue.result_events[
                    task_id
                ].set()  # Signal that the result is available
                self.is_free = True
        except asyncio.CancelledError:
            pass
