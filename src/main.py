import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from worker.worker import get_video_size, get_video_length, split_video_by_seconds, convert_to_720p


def main():
    # Replace with your actual MP4 file path
    input_video = "test.mov"  # Put your MP4 file path here
    
    # Check if file exists
    if not os.path.exists(input_video):
        print(f"Error: File {input_video} not found!")
        print("Please put an MP4 file in the current directory or update the path.")
        return
    
    print(f"Testing video: {input_video}")
    print("=" * 50)
    
    # Test 1: Get video size
    print("1. Getting video size...")
    size = get_video_size(input_video)
    if size > 0:
        print(f"   Video size: {size} bytes ({size / 1024 / 1024:.2f} MB)")
    else:
        print("   Failed to get video size")
    
    # Test 2: Get video length
    print("\n2. Getting video length...")
    try:
        length = get_video_length(input_video)
        print(f"   Video length: {length} seconds ({length // 60}:{length % 60:02d})")
    except Exception as e:
        print(f"   Error getting video length: {e}")
        return
    
    # Test 3: Split video into chunks
    print("\n3. Splitting video into 30-second chunks...")
    output_dir = "output_chunks"
    try:
        split_video_by_seconds(
            filename=input_video,
            split_length=30,  # 30 seconds per chunk
            output_dir=output_dir,
            video_length=length
        )
        print(f"   Video split successfully! Check {output_dir}/ folder")
        
        # List the created files
        if os.path.exists(output_dir):
            chunks = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
            print(f"   Created {len(chunks)} chunks: {chunks}")
    except Exception as e:
        print(f"   Error splitting video: {e}")
    
    # Test 4: Convert to 720p
    print("\n4. Converting to 720p...")
    output_720p = "output_720p.mp4"
    try:
        convert_to_720p(input_video, output_720p)
        print(f"   Video converted to 720p: {output_720p}")
        
        # Check the output file size
        new_size = get_video_size(output_720p)
        if new_size > 0:
            print(f"   New file size: {new_size} bytes ({new_size / 1024 / 1024:.2f} MB)")
    except Exception as e:
        print(f"   Error converting to 720p: {e}")
    
    print("\n" + "=" * 50)
    print("Testing completed!")

if __name__ == "__main__":
    main()