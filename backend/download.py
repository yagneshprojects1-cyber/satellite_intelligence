# The following code will only execute
# successfully when compression is complete

import kagglehub

# Download latest version
path = kagglehub.dataset_download("yagneshkotwal/sih-satellite-intelligence-data")

print("Path to dataset files:", path)