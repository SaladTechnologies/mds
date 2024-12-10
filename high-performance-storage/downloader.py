from config import Data_Get

folder = "high_performance_storage/results"

result = Data_Get("transcripts",folder,"test_results.csv")
print(result)