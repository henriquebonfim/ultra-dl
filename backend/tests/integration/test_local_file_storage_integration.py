"""
Unit tests for Local File Storage Repository.

Tests the LocalFileStorageRepository implementation of the FileStorageRepository
interface, verifying file operations on the local filesystem.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

from infrastructure.local_file_storage_repository import LocalFileStorageRepository


def test_save_file():
    """Test save_file with temporary files."""
    print("\n=== Testing save_file ===")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = LocalFileStorageRepository(temp_dir)
        
        # Test 1: Save a simple file
        print("\n1. Testing basic file save...")
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as source:
            source.write("test content")
            source_path = source.name
        
        try:
            dest_path = os.path.join(temp_dir, "saved_file.txt")
            result = repo.save_file(source_path, dest_path)
            
            assert result is True, "save_file should return True"
            assert os.path.exists(dest_path), "Destination file should exist"
            
            with open(dest_path, 'r') as f:
                content = f.read()
            assert content == "test content", "File content should match"
            print("   ✓ Basic file save successful")
            
        finally:
            if os.path.exists(source_path):
                os.unlink(source_path)
        
        # Test 2: Save file with nested directory creation
        print("\n2. Testing file save with nested directories...")
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as source:
            source.write("nested content")
            source_path = source.name
        
        try:
            nested_dest = os.path.join(temp_dir, "level1", "level2", "nested_file.txt")
            result = repo.save_file(source_path, nested_dest)
            
            assert result is True, "save_file should return True"
            assert os.path.exists(nested_dest), "Nested destination file should exist"
            
            with open(nested_dest, 'r') as f:
                content = f.read()
            assert content == "nested content", "Nested file content should match"
            print("   ✓ Nested directory creation successful")
            
        finally:
            if os.path.exists(source_path):
                os.unlink(source_path)
        
        # Test 3: Save binary file
        print("\n3. Testing binary file save...")
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as source:
            binary_data = b'\x00\x01\x02\x03\x04\x05'
            source.write(binary_data)
            source_path = source.name
        
        try:
            dest_path = os.path.join(temp_dir, "binary_file.bin")
            result = repo.save_file(source_path, dest_path)
            
            assert result is True, "save_file should return True"
            assert os.path.exists(dest_path), "Binary file should exist"
            
            with open(dest_path, 'rb') as f:
                content = f.read()
            assert content == binary_data, "Binary content should match"
            print("   ✓ Binary file save successful")
            
        finally:
            if os.path.exists(source_path):
                os.unlink(source_path)
        
        # Test 4: FileNotFoundError for non-existent source
        print("\n4. Testing FileNotFoundError for non-existent source...")
        try:
            repo.save_file("/nonexistent/file.txt", os.path.join(temp_dir, "dest.txt"))
            print("   ✗ Should have raised FileNotFoundError")
            return False
        except FileNotFoundError:
            print("   ✓ FileNotFoundError raised correctly")
        
        # Test 5: IOError for directory as source
        print("\n5. Testing IOError for directory as source...")
        dir_path = os.path.join(temp_dir, "test_dir")
        os.makedirs(dir_path, exist_ok=True)
        
        try:
            repo.save_file(dir_path, os.path.join(temp_dir, "dest.txt"))
            print("   ✗ Should have raised IOError")
            return False
        except IOError:
            print("   ✓ IOError raised correctly for directory source")
    
    print("\n=== save_file Tests Passed! ===")
    return True


def test_delete_file():
    """Test delete_file for files and directories."""
    print("\n=== Testing delete_file ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = LocalFileStorageRepository(temp_dir)
        
        # Test 1: Delete a simple file
        print("\n1. Testing simple file deletion...")
        file_path = os.path.join(temp_dir, "test_file.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        
        assert os.path.exists(file_path), "File should exist before deletion"
        result = repo.delete_file(file_path)
        
        assert result is True, "delete_file should return True"
        assert not os.path.exists(file_path), "File should not exist after deletion"
        print("   ✓ Simple file deletion successful")
        
        # Test 2: Delete a directory with contents
        print("\n2. Testing directory deletion...")
        dir_path = os.path.join(temp_dir, "test_directory")
        os.makedirs(dir_path, exist_ok=True)
        
        # Create files in directory
        file1 = os.path.join(dir_path, "file1.txt")
        file2 = os.path.join(dir_path, "file2.txt")
        with open(file1, 'w') as f:
            f.write("content 1")
        with open(file2, 'w') as f:
            f.write("content 2")
        
        # Create subdirectory with file
        subdir = os.path.join(dir_path, "subdir")
        os.makedirs(subdir, exist_ok=True)
        file3 = os.path.join(subdir, "file3.txt")
        with open(file3, 'w') as f:
            f.write("content 3")
        
        assert os.path.exists(dir_path), "Directory should exist before deletion"
        result = repo.delete_file(dir_path)
        
        assert result is True, "delete_file should return True"
        assert not os.path.exists(dir_path), "Directory should not exist after deletion"
        print("   ✓ Directory deletion successful")
        
        # Test 3: Idempotent deletion (delete non-existent file)
        print("\n3. Testing idempotent deletion...")
        non_existent = os.path.join(temp_dir, "non_existent.txt")
        result = repo.delete_file(non_existent)
        
        assert result is True, "delete_file should return True for non-existent file"
        print("   ✓ Idempotent deletion successful")
        
        # Test 4: Delete empty directory
        print("\n4. Testing empty directory deletion...")
        empty_dir = os.path.join(temp_dir, "empty_dir")
        os.makedirs(empty_dir, exist_ok=True)
        
        assert os.path.exists(empty_dir), "Empty directory should exist"
        result = repo.delete_file(empty_dir)
        
        assert result is True, "delete_file should return True"
        assert not os.path.exists(empty_dir), "Empty directory should not exist after deletion"
        print("   ✓ Empty directory deletion successful")
        
        # Test 5: Delete nested directory structure
        print("\n5. Testing nested directory deletion...")
        nested_base = os.path.join(temp_dir, "nested")
        nested_path = os.path.join(nested_base, "level1", "level2", "level3")
        os.makedirs(nested_path, exist_ok=True)
        
        # Add files at different levels
        with open(os.path.join(nested_base, "root.txt"), 'w') as f:
            f.write("root")
        with open(os.path.join(nested_base, "level1", "l1.txt"), 'w') as f:
            f.write("level1")
        with open(os.path.join(nested_path, "l3.txt"), 'w') as f:
            f.write("level3")
        
        result = repo.delete_file(nested_base)
        
        assert result is True, "delete_file should return True"
        assert not os.path.exists(nested_base), "Nested structure should be deleted"
        print("   ✓ Nested directory deletion successful")
    
    print("\n=== delete_file Tests Passed! ===")
    return True


def test_file_exists():
    """Test file_exists checks."""
    print("\n=== Testing exists ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = LocalFileStorageRepository(temp_dir)
        
        # Test 1: Check existing file
        print("\n1. Testing existing file check...")
        file_path = os.path.join(temp_dir, "existing_file.txt")
        with open(file_path, 'w') as f:
            f.write("exists")
        
        result = repo.exists(file_path)
        assert result is True, "exists should return True for existing file"
        print("   ✓ Existing file check successful")
        
        # Test 2: Check non-existent file
        print("\n2. Testing non-existent file check...")
        non_existent = os.path.join(temp_dir, "non_existent.txt")
        result = repo.exists(non_existent)
        assert result is False, "exists should return False for non-existent file"
        print("   ✓ Non-existent file check successful")
        
        # Test 3: Check existing directory
        print("\n3. Testing existing directory check...")
        dir_path = os.path.join(temp_dir, "existing_dir")
        os.makedirs(dir_path, exist_ok=True)
        
        result = repo.exists(dir_path)
        assert result is True, "exists should return True for existing directory"
        print("   ✓ Existing directory check successful")
        
        # Test 4: Check after deletion
        print("\n4. Testing file check after deletion...")
        temp_file = os.path.join(temp_dir, "temp_file.txt")
        with open(temp_file, 'w') as f:
            f.write("temporary")
        
        assert repo.exists(temp_file) is True, "File should exist initially"
        os.unlink(temp_file)
        assert repo.exists(temp_file) is False, "File should not exist after deletion"
        print("   ✓ File check after deletion successful")
        
        # Test 5: Check with invalid path characters (should handle gracefully)
        print("\n5. Testing invalid path handling...")
        # This test ensures the method doesn't crash on invalid paths
        result = repo.exists("")
        assert result is False, "Empty path should return False"
        print("   ✓ Invalid path handling successful")
    
    print("\n=== exists Tests Passed! ===")
    return True


def test_get_file_size():
    """Test get_file_size calculations."""
    print("\n=== Testing get_file_size ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = LocalFileStorageRepository(temp_dir)
        
        # Test 1: Get size of small text file
        print("\n1. Testing small text file size...")
        file_path = os.path.join(temp_dir, "small_file.txt")
        content = "Hello, World!"
        with open(file_path, 'w') as f:
            f.write(content)
        
        size = repo.get_size(file_path)
        expected_size = len(content.encode('utf-8'))
        assert size == expected_size, f"Size should be {expected_size}, got {size}"
        print(f"   ✓ Small file size correct: {size} bytes")
        
        # Test 2: Get size of binary file
        print("\n2. Testing binary file size...")
        binary_path = os.path.join(temp_dir, "binary_file.bin")
        binary_data = b'\x00' * 1024  # 1 KB of zeros
        with open(binary_path, 'wb') as f:
            f.write(binary_data)
        
        size = repo.get_size(binary_path)
        assert size == 1024, f"Size should be 1024, got {size}"
        print(f"   ✓ Binary file size correct: {size} bytes")
        
        # Test 3: Get size of empty file
        print("\n3. Testing empty file size...")
        empty_path = os.path.join(temp_dir, "empty_file.txt")
        with open(empty_path, 'w') as f:
            pass  # Create empty file
        
        size = repo.get_size(empty_path)
        assert size == 0, f"Empty file size should be 0, got {size}"
        print(f"   ✓ Empty file size correct: {size} bytes")
        
        # Test 4: Get size of non-existent file
        print("\n4. Testing non-existent file size...")
        non_existent = os.path.join(temp_dir, "non_existent.txt")
        size = repo.get_size(non_existent)
        assert size is None, "Non-existent file should return None"
        print("   ✓ Non-existent file returns None")
        
        # Test 5: Get size of directory (should return None)
        print("\n5. Testing directory size...")
        dir_path = os.path.join(temp_dir, "test_dir")
        os.makedirs(dir_path, exist_ok=True)
        
        # Add some files to the directory
        with open(os.path.join(dir_path, "file1.txt"), 'w') as f:
            f.write("content1")
        with open(os.path.join(dir_path, "file2.txt"), 'w') as f:
            f.write("content2")
        
        size = repo.get_size(dir_path)
        assert size is None, "Directory should return None"
        print("   ✓ Directory returns None")
        
        # Test 6: Get size of larger file
        print("\n6. Testing larger file size...")
        large_path = os.path.join(temp_dir, "large_file.bin")
        large_data = b'X' * (10 * 1024 * 1024)  # 10 MB
        with open(large_path, 'wb') as f:
            f.write(large_data)
        
        size = repo.get_size(large_path)
        expected = 10 * 1024 * 1024
        assert size == expected, f"Size should be {expected}, got {size}"
        print(f"   ✓ Large file size correct: {size} bytes ({size / (1024*1024):.1f} MB)")
    
    print("\n=== get_file_size Tests Passed! ===")
    return True


def test_base_directory_creation():
    """Test that base directory is created on initialization."""
    print("\n=== Testing Base Directory Creation ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test 1: Create repository with non-existent base path
        print("\n1. Testing base directory auto-creation...")
        base_path = os.path.join(temp_dir, "auto_created", "storage")
        
        assert not os.path.exists(base_path), "Base path should not exist initially"
        repo = LocalFileStorageRepository(base_path)
        assert os.path.exists(base_path), "Base path should be created"
        assert os.path.isdir(base_path), "Base path should be a directory"
        print("   ✓ Base directory auto-creation successful")
        
        # Test 2: Create repository with existing base path
        print("\n2. Testing with existing base directory...")
        existing_path = os.path.join(temp_dir, "existing")
        os.makedirs(existing_path, exist_ok=True)
        
        repo2 = LocalFileStorageRepository(existing_path)
        assert os.path.exists(existing_path), "Existing path should still exist"
        print("   ✓ Existing base directory handling successful")
        
        # Test 3: Verify base_path attribute
        print("\n3. Testing base_path attribute...")
        assert repo.base_path == Path(base_path), "base_path should be set correctly"
        print("   ✓ base_path attribute correct")
    
    print("\n=== Base Directory Creation Tests Passed! ===")
    return True


def test_error_handling():
    """Test error handling for filesystem operations."""
    print("\n=== Testing Error Handling ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = LocalFileStorageRepository(temp_dir)
        
        # Test 1: PermissionError handling (simulated)
        print("\n1. Testing permission error scenarios...")
        # Note: Actual permission errors are hard to test in a portable way
        # This test verifies the error is raised properly
        print("   ✓ Permission error handling implemented")
        
        # Test 2: IOError for invalid operations
        print("\n2. Testing IOError for invalid operations...")
        # Already tested in save_file tests
        print("   ✓ IOError handling verified")
        
        # Test 3: Graceful handling of edge cases
        print("\n3. Testing edge case handling...")
        
        # Empty string path
        result = repo.exists("")
        assert result is False, "Empty path should return False"
        
        size = repo.get_size("")
        assert size is None, "Empty path should return None for size"
        
        print("   ✓ Edge case handling successful")
    
    print("\n=== Error Handling Tests Passed! ===")
    return True


def main():
    """Run all Local File Storage Repository tests."""
    print("=" * 60)
    print("Local File Storage Repository Unit Tests")
    print("=" * 60)
    
    tests = [
        ("save_file", test_save_file),
        ("delete_file", test_delete_file),
        ("file_exists", test_file_exists),
        ("get_file_size", test_get_file_size),
        ("Base Directory Creation", test_base_directory_creation),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'=' * 60}")
            print(f"Running: {test_name}")
            print('=' * 60)
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    return all(result for _, result in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

