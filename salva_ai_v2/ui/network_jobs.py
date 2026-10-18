"""Rede em worker; a fila só é entregue pelo loop principal do Tk."""
from concurrent.futures import ThreadPoolExecutor
from queue import Queue,Empty
from uuid import uuid4


class TkNetworkRunner:
    def __init__(self,root):
        self.root=root;self.closed=False;self.queue=Queue();self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='email')
        self.pending={};self.timer=root.after(50,self._pump)

    def submit(self,job,on_success,on_error):
        if self.closed:raise RuntimeError('Executor encerrado.')
        token=str(uuid4());self.pending[token]=(on_success,on_error)
        def work():
            try:result=job()
            except Exception as error:self.queue.put((token,False,error))
            else:self.queue.put((token,True,result))
        self.pool.submit(work);return token

    def _pump(self):
        if self.closed:return
        while not self.closed:
            try:token,ok,result=self.queue.get_nowait()
            except Empty:break
            callbacks=self.pending.pop(token,None)
            if callbacks:
                try:callbacks[0 if ok else 1](result)
                except Exception as error:self.root.report_callback_exception(type(error),error,error.__traceback__)
        if not self.closed:self.timer=self.root.after(50,self._pump)

    def close(self):
        if self.closed:return
        self.closed=True;self.pending.clear()
        self.root.after_cancel(self.timer);self.pool.shutdown(wait=False,cancel_futures=True)
