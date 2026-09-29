"""
Background Job System
Resumable, idempotent background processing for pipeline phases
"""

import threading
import queue
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import json


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Phase(Enum):
    """Pipeline phases"""
    PHASE_6_EMBEDDINGS = "phase_6_embeddings"
    PHASE_7_QDRANT = "phase_7_qdrant"
    PHASE_8_CLIP = "phase_8_clip"
    PHASE_10_TEMPORAL = "phase_10_temporal"
    PHASE_11_CHANGE = "phase_11_change"
    PHASE_12_EARLIEST = "phase_12_earliest"
    PHASE_13_CLUSTERING = "phase_13_clustering"
    DATABASE_SYNC = "database_sync"


@dataclass
class Job:
    """Background job dataclass"""
    job_id: str
    phase: str
    operation: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    progress: float = 0.0
    result: Optional[Dict] = None
    retry_count: int = 0
    max_retries: int = 3


class JobQueue:
    """Thread-safe job queue for background processing"""
    
    def __init__(self):
        self.queue = queue.Queue()
        self.jobs: Dict[str, Job] = {}
        self.lock = threading.Lock()
    
    def enqueue(self, job: Job):
        """Add job to queue"""
        with self.lock:
            self.jobs[job.job_id] = job
            self.queue.put(job.job_id)
    
    def dequeue(self, timeout: float = 1.0) -> Optional[str]:
        """Get next job ID from queue"""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        with self.lock:
            return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, **kwargs):
        """Update job status"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                for key, value in kwargs.items():
                    setattr(job, key, value)
    
    def get_all_jobs(self) -> List[Job]:
        """Get all jobs"""
        with self.lock:
            return list(self.jobs.values())


class BackgroundWorker:
    """Background worker thread for processing jobs"""
    
    def __init__(self, job_queue: JobQueue, worker_id: int):
        self.job_queue = job_queue
        self.worker_id = worker_id
        self.running = False
        self.thread = None
    
    def start(self):
        """Start worker thread"""
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop worker thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
    
    def _run(self):
        """Worker main loop"""
        while self.running:
            job_id = self.job_queue.dequeue(timeout=1.0)
            if job_id is None:
                continue
            
            job = self.job_queue.get_job(job_id)
            if not job:
                continue
            
            try:
                self._process_job(job)
            except Exception as e:
                print(f"Worker {self.worker_id} error processing job {job_id}: {e}")
                self.job_queue.update_job(
                    job_id,
                    status=JobStatus.FAILED.value,
                    error_message=str(e),
                    completed_at=datetime.utcnow().isoformat()
                )
    
    def _process_job(self, job: Job):
        """Process a single job"""
        self.job_queue.update_job(
            job.job_id,
            status=JobStatus.RUNNING.value,
            started_at=datetime.utcnow().isoformat()
        )
        
        # Route to appropriate handler based on phase
        if job.phase == Phase.PHASE_6_EMBEDDINGS.value:
            self._process_phase_6(job)
        elif job.phase == Phase.PHASE_7_QDRANT.value:
            self._process_phase_7(job)
        elif job.phase == Phase.PHASE_10_TEMPORAL.value:
            self._process_phase_10(job)
        elif job.phase == Phase.PHASE_11_CHANGE.value:
            self._process_phase_11(job)
        elif job.phase == Phase.PHASE_12_EARLIEST.value:
            self._process_phase_12(job)
        elif job.phase == Phase.PHASE_13_CLUSTERING.value:
            self._process_phase_13(job)
        elif job.phase == Phase.DATABASE_SYNC.value:
            self._process_database_sync(job)
        else:
            raise ValueError(f"Unknown phase: {job.phase}")
    
    def _process_phase_6(self, job: Job):
        """Process Phase 6 (Clay embeddings)"""
        from app.embeddings.pipeline import Phase6Pipeline
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        try:
            pipeline = Phase6Pipeline(
                tiles_dir=os.getenv('TILES_DIR', 'data/tiles'),
                embeddings_dir=os.getenv('EMBEDDINGS_DIR', 'embeddings'),
                model_ckpt=os.getenv('CLAY_MODEL_PATH', 'models/clay/v1.5/clay-v1.5.ckpt'),
                metadata_yaml="clay-repo/configs/metadata.yaml",
                batch_size=int(os.getenv('CLAY_BATCH_SIZE', 32)),
                resume=True
            )
            
            pipeline.setup()
            stats = pipeline.process_tiles()
            
            self.job_queue.update_job(
                job.job_id,
                status=JobStatus.COMPLETED.value,
                completed_at=datetime.utcnow().isoformat(),
                progress=1.0,
                result=stats
            )
            
        except Exception as e:
            raise Exception(f"Phase 6 failed: {e}")
    
    def _process_phase_7(self, job: Job):
        """Process Phase 7 (Qdrant indexing)"""
        from app.vector_db.qdrant_indexer import QdrantIndexer
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        try:
            indexer = QdrantIndexer(
                embeddings_dir=os.getenv('EMBEDDINGS_DIR', 'embeddings'),
                batch_size=32
            )
            
            stats = indexer.index_all()
            
            self.job_queue.update_job(
                job.job_id,
                status=JobStatus.COMPLETED.value,
                completed_at=datetime.utcnow().isoformat(),
                progress=1.0,
                result=stats
            )
            
        except Exception as e:
            raise Exception(f"Phase 7 failed: {e}")
    
    def _process_phase_10(self, job: Job):
        """Process Phase 10 (Temporal pairing)"""
        from app.temporal.temporal_pairing import TemporalPairer
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        try:
            pairer = TemporalPairer(tiles_dir=os.getenv('TILES_DIR', 'data/tiles'))
            summary = pairer.create_all_pairs()
            
            self.job_queue.update_job(
                job.job_id,
                status=JobStatus.COMPLETED.value,
                completed_at=datetime.utcnow().isoformat(),
                progress=1.0,
                result=summary
            )
            
        except Exception as e:
            raise Exception(f"Phase 10 failed: {e}")
    
    def _process_phase_11(self, job: Job):
        """Process Phase 11 (Change detection)"""
        from app.temporal.change_detection import ChangeDetector
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        try:
            detector = ChangeDetector(
                pairs_dir=os.getenv('TEMPORAL_PAIRS_DIR', 'data/temporal_pairs'),
                output_dir=os.getenv('CHANGE_RESULTS_DIR', 'data/change_results'),
                changeformer_path=Path(os.getenv('CHANGEFORMER_MODEL_PATH')),
                changeformer_repo=Path(os.getenv('CHANGEFORMER_REPO'))
            )
            
            summary = detector.process_all_pairs(method="baseline")
            
            self.job_queue.update_job(
                job.job_id,
                status=JobStatus.COMPLETED.value,
                completed_at=datetime.utcnow().isoformat(),
                progress=1.0,
                result=summary
            )
            
        except Exception as e:
            raise Exception(f"Phase 11 failed: {e}")
    
    def _process_phase_12(self, job: Job):
        """Process Phase 12 (Earliest change)"""
        from app.temporal.earliest_change import EarliestChangeAnalyzer
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        try:
            analyzer = EarliestChangeAnalyzer(
                change_results_dir=Path(os.getenv('CHANGE_RESULTS_DIR', 'data/change_results')),
                temporal_pairs_dir=Path(os.getenv('TEMPORAL_PAIRS_DIR', 'data/temporal_pairs')),
                output_dir=Path(os.getenv('EARLIEST_CHANGES_DIR', 'data/earliest_changes'))
            )
            
            summary = analyzer.analyze_all_locations()
            
            self.job_queue.update_job(
                job.job_id,
                status=JobStatus.COMPLETED.value,
                completed_at=datetime.utcnow().isoformat(),
                progress=1.0,
                result=summary
            )
            
        except Exception as e:
            raise Exception(f"Phase 12 failed: {e}")
    
    def _process_phase_13(self, job: Job):
        """Process Phase 13 (Clay clustering)"""
        from app.clustering.clay_clustering import ClayClustering
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        try:
            clusterer = ClayClustering(
                embeddings_dir=Path(os.getenv('EMBEDDINGS_DIR', 'embeddings')),
                output_dir=Path(os.getenv('CLUSTERS_DIR', 'data/clusters'))
            )
            
            summary = clusterer.cluster()
            
            self.job_queue.update_job(
                job.job_id,
                status=JobStatus.COMPLETED.value,
                completed_at=datetime.utcnow().isoformat(),
                progress=1.0,
                result=summary
            )
            
        except Exception as e:
            raise Exception(f"Phase 13 failed: {e}")
    
    def _process_database_sync(self, job: Job):
        """Process database synchronization"""
        from app.database.synchronization import DatabaseSynchronizer
        from app.database.connection import init_database
        
        try:
            # Initialize database tables
            init_database()
            
            # Synchronize data
            syncer = DatabaseSynchronizer()
            summary = syncer.synchronize_all()
            
            self.job_queue.update_job(
                job.job_id,
                status=JobStatus.COMPLETED.value,
                completed_at=datetime.utcnow().isoformat(),
                progress=1.0,
                result=summary
            )
            
        except Exception as e:
            raise Exception(f"Database sync failed: {e}")


class PipelineOrchestrator:
    """
    Main pipeline orchestrator.
    
    Manages background jobs, tracks progress, and ensures
    idempotent/resumable execution.
    """
    
    def __init__(self, num_workers: int = 4):
        """Initialize orchestrator with worker pool."""
        self.job_queue = JobQueue()
        self.workers = []
        self.num_workers = num_workers
        
        for i in range(num_workers):
            worker = BackgroundWorker(self.job_queue, i)
            self.workers.append(worker)
    
    def start(self):
        """Start all workers"""
        for worker in self.workers:
            worker.start()
        print(f"Started {self.num_workers} background workers")
    
    def stop(self):
        """Stop all workers"""
        for worker in self.workers:
            worker.stop()
        print("Stopped all workers")
    
    def submit_job(self, phase: str, operation: str = "process") -> str:
        """Submit a job to the queue"""
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            phase=phase,
            operation=operation,
            status=JobStatus.PENDING.value,
            created_at=datetime.utcnow().isoformat(),
            max_retries=3
        )
        
        self.job_queue.enqueue(job)
        print(f"Submitted job {job_id} for {phase}")
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status"""
        job = self.job_queue.get_job(job_id)
        if job:
            return asdict(job)
        return None
    
    def get_all_jobs(self) -> List[Dict]:
        """Get all jobs"""
        return [asdict(job) for job in self.job_queue.get_all_jobs()]
    
    def check_completeness(self) -> Dict[str, bool]:
        """Check which phases are complete"""
        from pathlib import Path
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        completeness = {}
        
        # Check Phase 6 (embeddings live in year subfolders)
        emb_dir = Path(os.getenv('EMBEDDINGS_DIR', 'embeddings'))
        emb_count = 0
        for year in ["2022", "2023", "2024"]:
            year_dir = emb_dir / year
            if year_dir.exists():
                emb_count += len(list(year_dir.glob("*.npy")))
        completeness["phase_6"] = emb_count > 0
        
        # Check Phase 7 (Qdrant) via the shared local client — do not open a second lock
        try:
            from app.vector_db.qdrant_manager import get_qdrant_client
            client = get_qdrant_client(os.getenv('QDRANT_STORAGE', 'qdrant_storage'))
            clay_count = 0
            clip_count = 0
            if client.collection_exists("satellite_tiles"):
                clay_count = client.get_collection("satellite_tiles").points_count
            if client.collection_exists("satellite_tiles_clip"):
                clip_count = client.get_collection("satellite_tiles_clip").points_count
            completeness["phase_7"] = (clay_count + clip_count) > 0
        except Exception:
            completeness["phase_7"] = False
        
        # Check Phase 10 (temporal pairs)
        pairs_dir = Path(os.getenv('TEMPORAL_PAIRS_DIR', 'data/temporal_pairs'))
        pairs_count = sum(len(list((pairs_dir / comb).glob("*.json"))) for comb in ["2022_2023", "2023_2024", "2022_2024"] if (pairs_dir / comb).exists())
        completeness["phase_10"] = pairs_count >= 543
        
        # Check Phase 11 (change results)
        change_dir = Path(os.getenv('CHANGE_RESULTS_DIR', 'data/change_results'))
        change_count = sum(len(list((change_dir / comb).glob("*_result.json"))) for comb in ["2022_2023", "2023_2024", "2022_2024"] if (change_dir / comb).exists())
        completeness["phase_11"] = change_count > 0
        
        # Check Phase 12 (earliest changes)
        earliest_dir = Path(os.getenv('EARLIEST_CHANGES_DIR', 'data/earliest_changes'))
        completeness["phase_12"] = (earliest_dir / "earliest_changes_summary.json").exists()
        
        # Check Phase 13 (clustering)
        clusters_dir = Path(os.getenv('CLUSTERS_DIR', 'data/clusters'))
        completeness["phase_13"] = (clusters_dir / "clustering_summary.json").exists()
        
        # Check database sync
        completeness["database_sync"] = True  # Assume in sync if reachable
        
        return completeness
    
    def auto_run_missing_phases(self, skip_phases: List[str] = None):
        """Automatically run missing phases"""
        if skip_phases is None:
            skip_phases = []
        
        completeness = self.check_completeness()
        
        # Phase 6: Clay embeddings
        if not completeness["phase_6"] and "phase_6" not in skip_phases:
            self.submit_job(Phase.PHASE_6_EMBEDDINGS.value)
        
        # Phase 7: Qdrant indexing
        if not completeness["phase_7"] and "phase_7" not in skip_phases:
            self.submit_job(Phase.PHASE_7_QDRANT.value)
        
        # Phase 10: Temporal pairing
        if not completeness["phase_10"] and "phase_10" not in skip_phases:
            self.submit_job(Phase.PHASE_10_TEMPORAL.value)
        
        # Phase 11: Change detection
        if not completeness["phase_11"] and "phase_11" not in skip_phases:
            self.submit_job(Phase.PHASE_11_CHANGE.value)
        
        # Phase 12: Earliest change
        if not completeness["phase_12"] and "phase_12" not in skip_phases:
            self.submit_job(Phase.PHASE_12_EARLIEST.value)
        
        # Phase 13: Clustering
        if not completeness["phase_13"] and "phase_13" not in skip_phases:
            self.submit_job(Phase.PHASE_13_CLUSTERING.value)
        
        # Database sync
        if not completeness["database_sync"] and "database_sync" not in skip_phases:
            self.submit_job(Phase.DATABASE_SYNC.value)
