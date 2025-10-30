from asyncio import Lock, get_running_loop, sleep, timeout
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, List
from time import time
from uuid import uuid4 as uuid

from vira.types import TaskHandlerType

@dataclass
class TaskParams:
    data: Any = None

@dataclass
class Task:
    handler: TaskHandlerType
    params: TaskParams
    timeout_after: int =  5
    max_retries: int = 3
    _attempts: int = field(default=1, init=False, repr=False)

    def increment_attempts(self):
        self._attempts += 1

    def get_attempts(self):
        return self._attempts

def create_task(handler: TaskHandlerType, params: TaskParams = TaskParams(), **kwargs) -> Task:
    return Task(handler, params, **kwargs)

def cancel_if_server_is_shutting_down(return_value: Any = None) -> Any:
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if self._is_server_shutting_down:
                return return_value
            return await func(self, *args, **kwargs)

        return wrapper
    return decorator


class BackgroundTasks:
    
    def __init__(self, max_running_tasks: int = 5):
        assert isinstance(max_running_tasks, int) and max_running_tasks > 0, "max_running_tasks must be a positive integer"
        
        self.max_running_tasks = max_running_tasks
        
        self._is_server_shutting_down = False
        self._tasks_map: Dict[str, Task] = {}
        self._on_going_tasks = 0
        self._lock = Lock()
        
    async def shutdown(self, timeout: float = 30.0) -> None:
        self._is_server_shutting_down = True
        print("Shutting down background tasks")
        start_time = time()
        
        await self._clean_queue()
        
        while (time() - start_time) < timeout:
            async with self._lock:
                if self._on_going_task <= 0:
                    return
            
            await sleep(0.2)
            
        async with self._lock:
            if self._on_going_tasks > 0:
                print(f"Warning: {self._on_going_tasks} background tasks are still running after shutdown timeout")
        
    async def _clean_queue(self):
        async with self._lock:
            while not self._task_queue.empty():
                _id = await self._task_queue.get()
                print(f"Removing task {_id} from queue due to shutdown")
                self._task_queue.task_done()
                
    @staticmethod
    async def _generate_task_id(handler_name: str) -> str:
        _id = str(uuid())
        timestamp = int(time())
        
        return f"{handler_name}_{_id}_{timestamp}"
    
    @cancel_if_server_is_shutting_down(return_value=None)
    async def add_tasks(self, tasks: List[Task]) -> None:
        async with self._lock:
            print(f"Adding task: {len(tasks)}")
            for task in tasks:
                task_id = self._generate_task_id(task.handler.__name__)
                self._tasks_map[task_id] = task
                await self._task_queue.put(task_id)
                
    @cancel_if_server_is_shutting_down(return_value=[])
    async def _get_tasks_to_process(self) -> List[str]:
        to_process = []
        async with self._lock:
            if self._task_queue.empty() or self._on_going_tasks == self.max_running_tasks:
                return to_process

            for i in range(self.max_running_tasks - self._on_going_tasks):
                if self._task_queue.empty():
                    break
                task_id = await self._task_queue.get()
                to_process.append(task_id)
                self._task_queue.task_done()
                self._on_going_tasks += 1

        return to_process

    @cancel_if_server_is_shutting_down(return_value=None)
    async def _put_back_to_queue_if_allowed(self, task_id: str) -> bool:
        task = self._tasks_map.get(task_id)
        if task is None:
            return False

        if task.get_attempts() >= task.max_retries:
            print(f"task retry count exceeded: {task_id}")
            return False

        task.increment_attempts()
        async with self._lock:
            await self._task_queue.put(task_id)

        return True

    async def _run_task(self, target: str) -> None:
        enqueued = False
        try:
            print(f"trying to process: {target}")
            async with timeout(self._tasks_map[target].timeout_after):
                task = self._tasks_map[target]
                await task.handler(task.params)
                print(f"finished task: {target}")

        except TimeoutError:
            print(f"task timeout: {target}")
            enqueued = await self._put_back_to_queue_if_allowed(target)
        except Exception as e:
            print(f"task error: {target} {e}")
            # exceptions should be handled within the handler
        finally:
            if not enqueued:
                del self._tasks_map[target]
            async with self._lock:
                self._on_going_tasks -= 1

    @cancel_if_server_is_shutting_down(return_value=None)
    async def run_tasks(self) -> None:
        print(f"running tasks: {self._on_going_tasks}")
        to_process = await self._get_tasks_to_process()

        print(f"tasks to process: {to_process}")
        running_loop = get_running_loop()

        for task_id in to_process:
            print(f"running task: {task_id}")
            running_loop.create_task(self._run_task(task_id))

        print(f"on going tasks: {self._on_going_tasks}")