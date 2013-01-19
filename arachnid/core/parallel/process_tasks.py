''' Common parallel/serial design patterns

This module defines a set of common tasks that can be performed in parallel or serial.

.. Created on Jun 23, 2012
.. codeauthor:: Robert Langlois <rl2528@columbia.edu>
'''

import process_queue
import logging, numpy

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

def process_mp(process, vals, worker_count, init_process=None, **extra):
    ''' Generator that runs a process functor in parallel (or serial if worker_count 
        is less than 2) over a list of given data values and returns the result
        
    :Parameters:
    
    process : function
              Functor to be run in parallel (or serial if worker_count is less than 2)
    vals : list
           List of items to process in parallel
    worker_count : int
                    Number of processes to run in parallel
    init_process : function
                   Initalize the parameters for the child process
    extra : dict
            Unused keyword arguments
    
    :Returns:
        
        val : object
              Return value of process functor
    '''
    
    if len(vals) < worker_count: worker_count = len(vals)
    
    if worker_count > 1:
        qout = process_queue.start_workers_with_output(vals, process, worker_count, init_process, **extra)
        index = 0
        while index < len(vals):
            val = qout.get()
            if isinstance(val, process_queue.ProcessException):
                index = 0
                while index < worker_count:
                    if qout.get() is None:
                        index += 1;
                raise val
            if val is None: continue
            index += 1
            yield val
    else:
        logging.debug("Running with single process: %d"%len(vals))
        for i, val in enumerate(vals):
            yield i, process(val, **extra)
            
def iterate_reduce(for_func, worker, thread_count, queue_limit=None, **extra):
    ''' Iterate over the input value and reduce after finished processing
    '''
    
    if thread_count < 2:
        yield worker(enumerate(for_func), process_number=0, **extra)
        return
    
    
    def queue_iterator(qin):
        while True:
            val = qin.get()
            if val is None: break
            yield val
    
    def iterate_reduce_worker(qin, qout, process_number, process_limit, extra):
        val = None
        try:
            val = worker(queue_iterator(qin), process_number=process_number, **extra)
        except:
            _logger.exception("Error in child process")
            while True:
                val = qin.get()
                if val is None: break
        finally:
            qout.put(val)
            #qin.get()
    
    if queue_limit is None: queue_limit = thread_count*8
    else: queue_limit *= thread_count
    
    qin, qout = process_queue.start_raw_enum_workers(iterate_reduce_worker, thread_count, queue_limit, extra)
    for val in enumerate(for_func):
        qin.put(val)
    for i in xrange(thread_count): qin.put(None)
    #qin.join()
    
    for i in xrange(thread_count):
        val = qout.get()
        #qin.put(None)
        if val is None: raise ValueError, "Exception in child process"
        yield val
    

def map_reduce(for_func, worker, shape, max_length, thread_count=0, **extra):
    ''' Generator to process collection of arrays in parallel
    
    :Parameters:
    
    for_func : func
               Generate a list of data
    worker : function
           Function to preprocess the images
    thread_count : int
                   Number of threads
    shape : int
            Shape of worker result array
    extra : dict
            Unused keyword arguments
    
    :Returns:
    
    index : int
            Yields index of output array
    out : array
          Yields output array of worker
    '''
    
    if thread_count < 2:
        for i, val in enumerate(for_func):
            res = worker(val, i, **extra)
            yield i, res
    else:
        lock = process_queue.multiprocessing.Lock()
        length = numpy.prod(shape)*thread_count
        res, shmem_res = process_queue.create_global_dense_matrix( ( max(length, max_length), 1 )  )
        qin, qout = process_queue.start_raw_enum_workers(map_reduce_worker, thread_count, thread_count, worker, shmem_res, shape, lock, extra)
        res1 = res[:length].reshape((thread_count, numpy.prod(shape)))
        try:
            total = 0
            lock.acquire()
            for i, val in enumerate(for_func):
                if i >= (thread_count):
                    pos = qout.get() #if i > thread_count else i
                    if pos is None or pos == -1: raise ValueError, "Error occured in process1: %s"%str(pos)
                    pos, idx = pos
                else: 
                    pos = i
                    total += 1
                res1[pos, :] = val.ravel()
                qin.put((pos,i))
            for i in xrange(thread_count):
                pos = qout.get()
                if pos is None: raise ValueError, "Error occured in process2: %s - %d"%(str(pos), i)
                if isinstance(pos, tuple) and pos[0] is None: raise pos[1]
                qin.put((-1,-1))
            for i in xrange(thread_count):
                pos = qout.get()
                if pos is None: raise ValueError, "Error occured in process2: %s - %d"%(str(pos), i)
                if isinstance(pos, tuple) and pos[0] is None: raise pos[1]
            lock.release()
            done = 0
            type = 2
            while done < thread_count: # reduce
                _logger.error("Get: %d"%done)
                qin.put(type)
                type = qout.get()
                if type is None:
                    raise ValueError, "Exception in process"
                if type == -1:
                    done += 1
                    #qin.put(3)
                    type=2
                else:
                    if isinstance(type, tuple):
                        _logger.error("type=%s"%str(type))
                        raise ValueError, "problem"
                    yield type, res.ravel()
        except:
            for i in xrange(thread_count): 
                qin.put((-1, -1))
                #pos = qout.get()
            raise
    raise StopIteration

def map_reduce_worker(qin, qout, process_number, process_limit, worker, shmem_val, shape, lock, extra):
    ''' Worker in each process that preprocesses the images
    
    :Parameters:
    
    qin : multiprocessing.Queue
          Queue with index for input images in shared array
    qout : multiprocessing.Queue
           Queue with index and offset for the output images in shared array
    process_number : int
                     Process number
    process_limit : int
                    Number of processes
    worker : function
             Function to preprocess the images
    shmem_img : multiprocessing.RawArray
                Shared memory image array
    shape : tuple
            Dimensions of the shared memory array
    extra : dict
            Keyword arguments
    '''
    
    val = process_queue.recreate_global_dense_matrix(shmem_val)
    n = numpy.prod(shape)
    shmem = val[:n*process_limit].reshape((process_limit, n))
    try:
        #for tmp in queue_iterator(qin, qout, shmem, shape):
        #    pass
        #results = []
        #results = worker(queue_iterator(qin, qout, shmem, shape), **extra)
        results = worker(qin, qout, shmem, shape, process_limit, process_number, **extra)
    except Exception, ex:
        _logger.exception("Problem in iterator")
        qout.put((None, ex))
        raise
    finally:
        qout.put(-1)
    
    lock.acquire()
    _logger.error("Have lock: %d"%process_number)
    try:
        val = val.ravel()
        i = 0
        for res in results:
            if not hasattr(res, 'ndim'): continue
            pos = qin.get()
            if pos < 0: raise ValueError, "Terminated"
            res = res.ravel()
            _logger.error("send: %d - %s"%(len(res), str(pos)))
            val[:res.shape[0]] = res
            if hasattr(qin, "task_done"):  qin.task_done()
            qout.put(i)
            i += 1
        qout.put(-1)
        pos = qin.get()
    except:
        _logger.exception("Worker terminated with exception")
        qout.put(None)
        raise
    finally:
        _logger.error("Release lock: %d - %s"%(process_number, str(pos)))
        lock.release()
        #qout.put(-1)

def queue_iterator(qin, qout, shmem, shape):
    '''
    '''
    
    while True:
        pos = qin.get()
        if pos is None or pos[0] == -1: 
            if hasattr(qin, "task_done"):  qin.task_done()
            break
        pos, idx = pos
        yield idx, shmem[pos].reshape(shape)
        qout.put((pos, idx))
        
def for_process_mp(for_func, worker, shape, thread_count=0, queue_limit=None, **extra):
    ''' Generator to process collection of arrays in parallel
    
    :Parameters:
    
    for_func : func
               Generate a list of data
    work : function
           Function to preprocess the images
    thread_count : int
                   Number of threads
    shape : int
            Shape of worker result array
    extra : dict
            Unused keyword arguments
    
    :Returns:
    
    index : int
            Yields index of output array
    out : array
          Yields output array of worker
    '''
    
    if thread_count < 2:
        for i, val in enumerate(for_func):
            res = worker(val, i, **extra)
            yield i, res
    else:
        if queue_limit is None: queue_limit = thread_count*8
        else: queue_limit *= thread_count
        qin, qout = process_queue.start_raw_enum_workers(process_worker2, thread_count, queue_limit, worker, extra)
        
        try:
            total = 0
            for i, val in enumerate(for_func):
                if i >= thread_count:
                    pos = qout.get() #if i > thread_count else i
                    if pos is None or pos == -1: raise ValueError, "Error occured in process: %d"%pos
                    res, idx = pos
                    yield idx, res
                else: 
                    pos = i
                    total += 1
                qin.put((val,i))
            for i in xrange(total):
                pos = qout.get()
                if pos is None or pos == -1: raise ValueError, "Error occured in process: %d"%pos
                res, idx = pos
                yield idx, res
        finally:
            #_logger.error("Terminating %d workers"%(thread_count))
            for i in xrange(thread_count): 
                qin.put((-1, -1))
                pos = qout.get()
                if pos != -1:
                    _logger.error("Wrong return value: %s"%str(pos))
                assert(pos==-1)
    raise StopIteration

def process_worker2(qin, qout, process_number, process_limit, worker, extra):
    ''' Worker in each process that preprocesses the images
    
    :Parameters:
    
    qin : multiprocessing.Queue
          Queue with index for input images in shared array
    qout : multiprocessing.Queue
           Queue with index and offset for the output images in shared array
    process_number : int
                     Process number
    process_limit : int
                    Number of processes
    worker : function
             Function to preprocess the images
    shmem_img : multiprocessing.RawArray
                Shared memory image array
    shape : tuple
            Dimensions of the shared memory array
    extra : dict
            Keyword arguments
    '''
    
    _logger.debug("Worker %d of %d - started"%(process_number, process_limit))
    try:
        while True:
            pos = qin.get()
            if pos is None or not hasattr(pos[0], 'ndim'): break
            res, idx = pos
            val = worker(res, idx, **extra)
            qout.put((val, idx))
        _logger.debug("Worker %d of %d - ending ..."%(process_number, process_limit))
        qout.put(-1)
    except:
        _logger.exception("Finished with error")
        qout.put(None)
    else:
        _logger.debug("Worker %d of %d - finished"%(process_number, process_limit))

def for_process_mp_shmem(for_func, worker, shape, thread_count=0, **extra):
    ''' Generator to process collection of arrays in parallel
    
    :Parameters:
    
    for_func : func
               Generate a list of data
    work : function
           Function to preprocess the images
    thread_count : int
                   Number of threads
    shape : int
            Shape of worker result array
    extra : dict
            Unused keyword arguments
    
    :Returns:
    
    index : int
            Yields index of output array
    out : array
          Yields output array of worker
    '''
    
    if thread_count < 2:
        for i, val in enumerate(for_func):
            res = worker(val, i, **extra)
            yield i, res
    else:
        length = numpy.prod(shape)
        res, shmem_res = process_queue.create_global_dense_matrix( ( thread_count, length )  )
        qin, qout = process_queue.start_raw_enum_workers(process_worker, thread_count, thread_count, worker, shmem_res, shape, extra)
        
        try:
            total = 0
            for i, val in enumerate(for_func):
                if i >= thread_count:
                    pos = qout.get() #if i > thread_count else i
                    if pos is None or pos == -1: raise ValueError, "Error occured in process: %d"%pos
                    pos, idx = pos
                    yield idx, res[pos]
                else: 
                    pos = i
                    total += 1
                res[pos, :] = val.ravel()
                qin.put((pos,i))
            for i in xrange(total):
                pos = qout.get()
                if pos is None or pos == -1: raise ValueError, "Error occured in process: %d"%pos
                pos, idx = pos
                yield idx, res[pos].reshape(shape)
        finally:
            #_logger.error("Terminating %d workers"%(thread_count))
            for i in xrange(thread_count): 
                qin.put((-1, -1))
                pos = qout.get()
                if pos != -1:
                    _logger.error("Wrong return value: %s"%str(pos))
                assert(pos==-1)
    raise StopIteration

def process_worker(qin, qout, process_number, process_limit, worker, shmem_res, shape, extra):
    ''' Worker in each process that preprocesses the images
    
    :Parameters:
    
    qin : multiprocessing.Queue
          Queue with index for input images in shared array
    qout : multiprocessing.Queue
           Queue with index and offset for the output images in shared array
    process_number : int
                     Process number
    process_limit : int
                    Number of processes
    worker : function
             Function to preprocess the images
    shmem_img : multiprocessing.RawArray
                Shared memory image array
    shape : tuple
            Dimensions of the shared memory array
    extra : dict
            Keyword arguments
    '''
    
    res = process_queue.recreate_global_dense_matrix(shmem_res)
    _logger.debug("Worker %d of %d - started"%(process_number, process_limit))
    try:
        while True:
            pos = qin.get()
            if pos is None or pos[0] == -1: break
            pos, idx = pos
            val = worker(res[pos, :].reshape(shape), idx, **extra)
            res[pos, :val.ravel().shape[0]] = val.ravel()
            qout.put((pos, idx))
        _logger.debug("Worker %d of %d - ending ..."%(process_number, process_limit))
        qout.put(-1)
    except:
        _logger.exception("Finished with error")
        qout.put(None)
    else:
        _logger.debug("Worker %d of %d - finished"%(process_number, process_limit))


    
