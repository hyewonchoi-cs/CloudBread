from fastapi import FastAPI
import time

app = FastAPI()

def find_primes(n):
    primes = []
    for i in range(2, n + 1):
        is_prime = True
        for j in range(2, int(i**0.5) + 1):
            if i % j == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(i)
    return primes

@app.get("/")
def run():
    start = time.time()
    find_primes(50000)
    end = time.time()
    return {"time": end - start}