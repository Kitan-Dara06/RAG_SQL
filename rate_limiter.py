"""
Rate limiter for OpenAI API calls to prevent excessive usage and costs.
Uses a token bucket algorithm for smooth rate limiting.
"""
import time
import threading
from functools import wraps
from config import RATE_LIMIT_PER_MINUTE
from logger import get_logger
from exceptions import RateLimitError

logger = get_logger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter using token bucket algorithm.
    
    Allows bursts up to max_calls, then enforces rate limit.
    """
    
    def __init__(self, max_calls_per_minute=None):
        """
        Initialize rate limiter.
        
        Args:
            max_calls_per_minute: Maximum API calls allowed per minute
        """
        self.max_calls = max_calls_per_minute or RATE_LIMIT_PER_MINUTE
        self.calls = []
        self.lock = threading.Lock()
        logger.info("Rate limiter initialized: %d calls/minute", self.max_calls)
    
    def wait_if_needed(self):
        """
        Check rate limit and wait if necessary.
        
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        with self.lock:
            now = time.time()
            
            # Remove calls older than 1 minute
            self.calls = [call_time for call_time in self.calls if now - call_time < 60]
            
            if len(self.calls) >= self.max_calls:
                # Calculate wait time
                oldest_call = self.calls[0]
                wait_time = 60 - (now - oldest_call)
                
                if wait_time > 0:
                    logger.warning("Rate limit reached (%d/%d calls). Waiting %.2f seconds", 
                                 len(self.calls), self.max_calls, wait_time)
                    time.sleep(wait_time)
                    # Clean up again after waiting
                    now = time.time()
                    self.calls = [call_time for call_time in self.calls if now - call_time < 60]
            
            # Record this call
            self.calls.append(now)
            logger.debug("API call recorded. Current rate: %d/%d calls in last minute", 
                        len(self.calls), self.max_calls)
    
    def __call__(self, func):
        """
        Decorator to apply rate limiting to a function.
        
        Usage:
            @rate_limiter
            def my_api_call():
                ...
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper


# Global rate limiter instance
openai_rate_limiter = RateLimiter()


def rate_limited(func):
    """
    Decorator for rate-limiting OpenAI API calls.
    
    Usage:
        @rate_limited
        def call_openai_api():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        openai_rate_limiter.wait_if_needed()
        return func(*args, **kwargs)
    return wrapper


if __name__ == "__main__":
    # Test rate limiter
    limiter = RateLimiter(max_calls_per_minute=5)
    
    print("Testing rate limiter with 5 calls/minute limit...")
    for i in range(7):
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        print(f"Call {i+1}: waited {elapsed:.2f}s")
