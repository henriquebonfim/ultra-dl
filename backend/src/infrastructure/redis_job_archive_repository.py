"""
Redis Job Archive Repository Implementation

Concrete Redis-based implementation of IJobArchiveRepository interface.
Provides job archive persistence with TTL and indexing for efficient queries.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.job_management.entities import JobArchive
from src.domain.job_management.repositories import IJobArchiveRepository


class RedisJobArchiveRepository(IJobArchiveRepository):
    """
    Redis-based implementation of IJobArchiveRepository.
    
    Stores archived job metadata with 30-day TTL and maintains indexes
    for efficient querying by status and date range.
    
    Key Schema:
        - archive:job:{job_id} -> JobArchive JSON (TTL: 30 days)
        - archive:index:status:{status} -> Sorted Set by archived_at timestamp
        - archive:index:date:{YYYY-MM-DD} -> Set of job_ids
    """
    
    KEY_PREFIX = "archive:job:"
    INDEX_PREFIX = "archive:index:"
    TTL_DAYS = 30
    
    def __init__(self, redis_client):
        """
        Initialize with Redis client.
        
        Args:
            redis_client: Redis client instance (redis.Redis)
        """
        self.redis = redis_client
        self.ttl_seconds = self.TTL_DAYS * 24 * 60 * 60  # 30 days in seconds
    
    def save(self, archive: JobArchive) -> bool:
        """
        Save archived job metadata with 30-day TTL.
        
        Also maintains indexes for querying:
        - Status index: Sorted set by archived_at timestamp
        - Date index: Set of job_ids for each date
        
        Args:
            archive: JobArchive to persist
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare keys
            job_key = f"{self.KEY_PREFIX}{archive.job_id}"
            status_index_key = f"{self.INDEX_PREFIX}status:{archive.status}"
            date_str = archive.archived_at.strftime("%Y-%m-%d")
            date_index_key = f"{self.INDEX_PREFIX}date:{date_str}"
            
            # Serialize archive
            archive_data = json.dumps(archive.to_dict())
            
            # Use pipeline for atomic operation
            pipeline = self.redis.pipeline()
            
            # 1. Save archive with TTL
            pipeline.setex(job_key, self.ttl_seconds, archive_data)
            
            # 2. Add to status index (sorted set by timestamp)
            archived_timestamp = archive.archived_at.timestamp()
            pipeline.zadd(status_index_key, {archive.job_id: archived_timestamp})
            pipeline.expire(status_index_key, self.ttl_seconds)
            
            # 3. Add to date index (set of job_ids)
            pipeline.sadd(date_index_key, archive.job_id)
            pipeline.expire(date_index_key, self.ttl_seconds)
            
            # Execute all operations atomically
            results = pipeline.execute()
            
            # Check if archive save succeeded (first operation)
            return results[0] is True
            
        except Exception as e:
            print(f"Error saving archive for job {archive.job_id}: {e}")
            return False
    
    def get(self, job_id: str) -> Optional[JobArchive]:
        """
        Retrieve archived job by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobArchive if found, None otherwise
        """
        try:
            job_key = f"{self.KEY_PREFIX}{job_id}"
            data = self.redis.get(job_key)
            
            if data is None:
                return None
            
            # Deserialize
            archive_dict = json.loads(
                data.decode('utf-8') if isinstance(data, bytes) else data
            )
            
            return JobArchive.from_dict(archive_dict)
            
        except Exception as e:
            print(f"Error retrieving archive for job {job_id}: {e}")
            return None
    
    def get_by_date_range(
        self, 
        start: datetime, 
        end: datetime
    ) -> List[JobArchive]:
        """
        Query archives by date range using date indexes.
        
        Iterates through each date in the range and retrieves all
        archived jobs for those dates.
        
        Args:
            start: Start of date range (inclusive)
            end: End of date range (inclusive)
            
        Returns:
            List of JobArchive instances within the date range
        """
        try:
            archives = []
            
            # Generate list of dates in range
            current_date = start.date()
            end_date = end.date()
            
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                date_index_key = f"{self.INDEX_PREFIX}date:{date_str}"
                
                # Get all job_ids for this date
                job_ids = self.redis.smembers(date_index_key)
                
                if job_ids:
                    # Retrieve archives in batch using pipeline
                    pipeline = self.redis.pipeline()
                    
                    for job_id in job_ids:
                        # Decode if bytes
                        job_id_str = (
                            job_id.decode('utf-8') 
                            if isinstance(job_id, bytes) 
                            else job_id
                        )
                        job_key = f"{self.KEY_PREFIX}{job_id_str}"
                        pipeline.get(job_key)
                    
                    results = pipeline.execute()
                    
                    # Deserialize and filter by time range
                    for result in results:
                        if result is not None:
                            try:
                                archive_dict = json.loads(
                                    result.decode('utf-8') 
                                    if isinstance(result, bytes) 
                                    else result
                                )
                                archive = JobArchive.from_dict(archive_dict)
                                
                                # Filter by exact time range
                                if start <= archive.archived_at <= end:
                                    archives.append(archive)
                                    
                            except Exception as e:
                                print(f"Error deserializing archive in date range query: {e}")
                                continue
                
                # Move to next date
                current_date += timedelta(days=1)
            
            return archives
            
        except Exception as e:
            print(f"Error querying archives by date range: {e}")
            return []
    
    def count_by_status(self, status: str) -> int:
        """
        Count archived jobs by final status using status index.
        
        Args:
            status: Status to count (e.g., 'completed', 'failed')
            
        Returns:
            Count of archived jobs with the specified status
        """
        try:
            status_index_key = f"{self.INDEX_PREFIX}status:{status}"
            
            # Use ZCARD to get count of items in sorted set
            count = self.redis.zcard(status_index_key)
            
            return count if count is not None else 0
            
        except Exception as e:
            print(f"Error counting archives by status {status}: {e}")
            return 0
