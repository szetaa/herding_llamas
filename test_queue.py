import asyncio
import uuid


# TaskQueue definition
class TaskQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.results = {}
        self.new_task_event = asyncio.Event()

    async def enqueue_task(self, task_func, skill_required):
        task_id = str(uuid.uuid4())
        await self.queue.put((task_id, task_func, skill_required))
        self.new_task_event.set()
        return task_id

    async def try_dequeue_task(self, skills):
        print("checking for skills: ", skills)
        if self.queue.empty():
            return None, None
        task_id, task_func, skill_required = await self.queue.get()
        if skill_required in skills:
            return task_id, task_func
        else:
            await self.queue.put((task_id, task_func, skill_required))
            return None, None


# Worker definition
class Worker:
    def __init__(self, task_queue, skills):
        self.task_queue = task_queue
        self.skills = skills
        self.is_free = True

    async def start(self):
        try:
            while True:
                task_id, task_func = await self.task_queue.try_dequeue_task(self.skills)
                print("RUNNING", task_id)

                if not task_id:  # If no task matches the skills
                    await self.task_queue.new_task_event.wait()
                    self.task_queue.new_task_event.clear()
                    continue  # Go back and check the queue again

                self.is_free = False
                result = await task_func()
                self.task_queue.results[task_id] = result
                self.is_free = True
        except asyncio.CancelledError:
            pass


# Sample task
async def sample_task(skill):
    await asyncio.sleep(2)
    print(f"Task completed for {skill}")


# Main function to run everything
async def main():
    task_queue = TaskQueue()

    skills_AB = ["skill_A", "skill_B"]
    skills_BC = ["skill_B", "skill_C"]

    asyncio.create_task(Worker(task_queue, skills_AB).start())
    asyncio.create_task(Worker(task_queue, skills_BC).start())

    # Enqueue tasks for demonstration
    a = await task_queue.enqueue_task(lambda: sample_task("skill_A"), "skill_A")
    print("queuing A", a)
    b = await task_queue.enqueue_task(lambda: sample_task("skill_B"), "skill_B")
    print("queuing B", b)
    c = await task_queue.enqueue_task(lambda: sample_task("skill_C"), "skill_C")
    print("queuing C", c)
    # Let it run for some time to process tasks
    await asyncio.sleep(10)


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
