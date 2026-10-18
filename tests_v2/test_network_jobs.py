import threading,time,tkinter as tk,unittest
from salva_ai_v2.ui.network_jobs import TkNetworkRunner
from tests_v2.support import DatabaseCase

class NetworkJobsTests(DatabaseCase):
    def test_worker_never_touches_tk_or_sqlite(self):
        root=tk.Tk();self.addCleanup(root.destroy)
        runner=TkNetworkRunner(root);self.addCleanup(runner.close)
        main=threading.get_ident();results=[]
        def complete(worker):
            self.assertEqual(threading.get_ident(),main)
            self.db.conn.execute('SELECT 1');results.append(worker)
        runner.submit(threading.get_ident,complete,lambda error:self.fail(str(error)))
        deadline=time.monotonic()+3
        while not results and time.monotonic()<deadline:root.update();time.sleep(.01)
        self.assertEqual(len(results),1);self.assertNotEqual(results[0],main)
        runner.submit(lambda:1,lambda _:self.fail('late callback'),lambda _:None)
        runner.close();root.update()
