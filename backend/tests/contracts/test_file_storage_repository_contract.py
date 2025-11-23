"""
File Storage Repository Contract Tests

Shared test suite for FileStorageRepository interface that can be run against any implementation.
This ensures all FileStorageRepository implementations (Local, GCS, S3, etc.) follow the same contract.

Run with: docker-compose exec backend python tests/contracts/test_file_storage_repository_contract.py
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Type

from domain.file_storage.storage_repository import IFileStorageRepository
from infrastructure.local_file_storage_repository import LocalFileStorageRepository


class FileStorageRepositoryContractTests:
    """
    Contract tests for IFileStorageRepository interface.
    
    Any implementation of IFileStorageRepository should pass these tests.
    These tests verify the core contract defined in the abstract interface.
    """
    
    def __init__(self, repository: IFileStorageRepository, test_prefix: str = "test"):
        self.repo = repository
        self.test_prefix = test_prefix
        self.test_files = []
        self.temp_dir = None
    
    def setup(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix=f"{self.test_prefix}_")
        self.test_files = []
    
    def cleanup(self):
        """Clean up test files and directories."""
        # Clean up tracked test files
        for file_path in self.test_files:
            try:
                if self.repo.file_exists(file_path):
                    self.repo.delete_file(file_path)
            except:
                pass
        
        # Clean up temp directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass
        
        self.test_files.clear()
        self.temp_dir = None
    
    def _create_temp_file(self, content: str = "test content", suffix: str = ".txt") -> str:
        """Create a temporary file with content."""
        with tempfile.NamedTemporaryFile(
            mode='w', 
            delete=False, 
            suffix=suffix,
            dir=self.temp_dir
        ) as f:
            f.write(content)
            return f.name
    
    def _create_temp_binary_file(self, content: bytes = b'\x00\x01\x02\x03', suffix: str = ".bin") -> str:
        """Create a temporary binary file with content."""
        with tempfile.NamedTemporaryFile(
            mode='wb', 
            delete=False, 
            suffix=suffix,
            dir=self.temp_dir
        ) as f:
            f.write(content)
            return f.name
    
    def test_save_file_basic(self) -> bool:
        """Test basic file save operation."""
        print("  Testing basic file save...")
        
        try:
            # Create source file
            source_path = self._create_temp_file("test content for save")
            dest_path = os.path.join(self.temp_dir, "saved_file.txt")
            self.test_files.append(dest_path)
            
            # Save file
            result = self.repo.save_file(source_path, dest_path)
            
            if not result:
                print("    ✗ save_file should return True")
                return False
            
            # Verify destination exists
            if not self.repo.file_exists(dest_path):
                print("    ✗ Destination file should exist after save")
                return False
            
            # Verify content (if possible to read)
            if os.path.exists(dest_path):
                with open(dest_path, 'r') as f:
                    content = f.read()
                if content != "test content for save":
                    print(f"    ✗ Content mismatch: got '{content}'")
                    return False
            
            print("    ✓ Basic file save successful")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_save_file_with_nested_directories(self) -> bool:
        """Test save_file creates nested directories."""
        print("  Testing save with nested directory creation...")
        
        try:
            # Create source file
            source_path = self._create_temp_file("nested content")
            dest_path = os.path.join(
                self.temp_dir, 
                "level1", "level2", "level3", "nested_file.txt"
            )
            self.test_files.append(dest_path)
            
            # Save file (should create directories)
            result = self.repo.save_file(source_path, dest_path)
            
            if not result:
                print("    ✗ save_file should return True")
                return False
            
            # Verify file exists
            if not self.repo.file_exists(dest_path):
                print("    ✗ Nested file should exist after save")
                return False
            
            print("    ✓ Nested directory creation successful")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_save_file_binary(self) -> bool:
        """Test save_file with binary content."""
        print("  Testing binary file save...")
        
        try:
            # Create binary source file
            binary_data = b'\x00\x01\x02\x03\x04\x05\xFF\xFE'
            source_path = self._create_temp_binary_file(binary_data)
            dest_path = os.path.join(self.temp_dir, "binary_file.bin")
            self.test_files.append(dest_path)
            
            # Save file
            result = self.repo.save_file(source_path, dest_path)
            
            if not result:
                print("    ✗ save_file should return True for binary file")
                return False
            
            # Verify file exists
            if not self.repo.file_exists(dest_path):
                print("    ✗ Binary file should exist after save")
                return False
            
            # Verify binary content (if possible to read)
            if os.path.exists(dest_path):
                with open(dest_path, 'rb') as f:
                    content = f.read()
                if content != binary_data:
                    print(f"    ✗ Binary content mismatch")
                    return False
            
            print("    ✓ Binary file save successful")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_save_file_nonexistent_source(self) -> bool:
        """Test save_file raises FileNotFoundError for non-existent source."""
        print("  Testing save with non-existent source...")
        
        try:
            nonexistent_source = os.path.join(self.temp_dir, "nonexistent_source.txt")
            dest_path = os.path.join(self.temp_dir, "dest.txt")
            
            # Should raise FileNotFoundError
            try:
                self.repo.save_file(nonexistent_source, dest_path)
                print("    ✗ Should have raised FileNotFoundError")
                return False
            except FileNotFoundError:
                print("    ✓ FileNotFoundError raised correctly")
                return True
            
        except Exception as e:
            print(f"    ✗ Test failed with unexpected exception: {e}")
            return False
    
    def test_delete_file_basic(self) -> bool:
        """Test basic file deletion."""
        print("  Testing basic file deletion...")
        
        try:
            # Create and save a file
            source_path = self._create_temp_file("delete me")
            dest_path = os.path.join(self.temp_dir, "to_delete.txt")
            self.repo.save_file(source_path, dest_path)
            
            # Verify file exists
            if not self.repo.file_exists(dest_path):
                print("    ✗ File should exist before deletion")
                return False
            
            # Delete file
            result = self.repo.delete_file(dest_path)
            
            if not result:
                print("    ✗ delete_file should return True")
                return False
            
            # Verify file no longer exists
            if self.repo.file_exists(dest_path):
                print("    ✗ File should not exist after deletion")
                return False
            
            print("    ✓ Basic file deletion successful")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_delete_file_directory(self) -> bool:
        """Test directory deletion with contents."""
        print("  Testing directory deletion...")
        
        try:
            # Create directory with files
            dir_path = os.path.join(self.temp_dir, "dir_to_delete")
            os.makedirs(dir_path, exist_ok=True)
            
            # Create files in directory
            file1 = os.path.join(dir_path, "file1.txt")
            file2 = os.path.join(dir_path, "file2.txt")
            with open(file1, 'w') as f:
                f.write("content1")
            with open(file2, 'w') as f:
                f.write("content2")
            
            # Create subdirectory with file
            subdir = os.path.join(dir_path, "subdir")
            os.makedirs(subdir, exist_ok=True)
            file3 = os.path.join(subdir, "file3.txt")
            with open(file3, 'w') as f:
                f.write("content3")
            
            # Verify directory exists
            if not self.repo.file_exists(dir_path):
                print("    ✗ Directory should exist before deletion")
                return False
            
            # Delete directory
            result = self.repo.delete_file(dir_path)
            
            if not result:
                print("    ✗ delete_file should return True for directory")
                return False
            
            # Verify directory no longer exists
            if self.repo.file_exists(dir_path):
                print("    ✗ Directory should not exist after deletion")
                return False
            
            print("    ✓ Directory deletion successful")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_delete_file_idempotent(self) -> bool:
        """Test delete_file is idempotent (deleting non-existent file succeeds)."""
        print("  Testing idempotent deletion...")
        
        try:
            nonexistent_path = os.path.join(self.temp_dir, "nonexistent_file.txt")
            
            # Delete non-existent file should succeed
            result = self.repo.delete_file(nonexistent_path)
            
            if not result:
                print("    ✗ delete_file should return True for non-existent file")
                return False
            
            print("    ✓ Idempotent deletion successful")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_file_exists_for_existing_file(self) -> bool:
        """Test file_exists returns True for existing file."""
        print("  Testing file_exists for existing file...")
        
        try:
            # Create file
            source_path = self._create_temp_file("exists")
            dest_path = os.path.join(self.temp_dir, "existing_file.txt")
            self.test_files.append(dest_path)
            self.repo.save_file(source_path, dest_path)
            
            # Check existence
            result = self.repo.file_exists(dest_path)
            
            if not result:
                print("    ✗ file_exists should return True for existing file")
                return False
            
            print("    ✓ Existing file check successful")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_file_exists_for_nonexistent_file(self) -> bool:
        """Test file_exists returns False for non-existent file."""
        print("  Testing file_exists for non-existent file...")
        
        try:
            nonexistent_path = os.path.join(self.temp_dir, "nonexistent.txt")
            
            # Check existence
            result = self.repo.file_exists(nonexistent_path)
            
            if result:
                print("    ✗ file_exists should return False for non-existent file")
                return False
            
            print("    ✓ Non-existent file check successful")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_file_exists_for_directory(self) -> bool:
        """Test file_exists returns True for existing directory."""
        print("  Testing file_exists for directory...")
        
        try:
            # Create directory
            dir_path = os.path.join(self.temp_dir, "existing_dir")
            os.makedirs(dir_path, exist_ok=True)
            self.test_files.append(dir_path)
            
            # Check existence
            result = self.repo.file_exists(dir_path)
            
            if not result:
                print("    ✗ file_exists should return True for existing directory")
                return False
            
            print("    ✓ Directory existence check successful")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_get_file_size_for_file(self) -> bool:
        """Test get_file_size returns correct size for file."""
        print("  Testing get_file_size for file...")
        
        try:
            # Create file with known content
            content = "Hello, World! This is a test file."
            source_path = self._create_temp_file(content)
            dest_path = os.path.join(self.temp_dir, "sized_file.txt")
            self.test_files.append(dest_path)
            self.repo.save_file(source_path, dest_path)
            
            # Get file size
            size = self.repo.get_file_size(dest_path)
            
            if size is None:
                print("    ✗ get_file_size should return size, not None")
                return False
            
            expected_size = len(content.encode('utf-8'))
            if size != expected_size:
                print(f"    ✗ Size mismatch: expected {expected_size}, got {size}")
                return False
            
            print(f"    ✓ File size correct: {size} bytes")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_get_file_size_for_binary_file(self) -> bool:
        """Test get_file_size for binary file."""
        print("  Testing get_file_size for binary file...")
        
        try:
            # Create binary file with known size
            binary_data = b'\x00' * 1024  # 1 KB
            source_path = self._create_temp_binary_file(binary_data)
            dest_path = os.path.join(self.temp_dir, "binary_sized.bin")
            self.test_files.append(dest_path)
            self.repo.save_file(source_path, dest_path)
            
            # Get file size
            size = self.repo.get_file_size(dest_path)
            
            if size is None:
                print("    ✗ get_file_size should return size for binary file")
                return False
            
            if size != 1024:
                print(f"    ✗ Size mismatch: expected 1024, got {size}")
                return False
            
            print(f"    ✓ Binary file size correct: {size} bytes")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_get_file_size_for_nonexistent_file(self) -> bool:
        """Test get_file_size returns None for non-existent file."""
        print("  Testing get_file_size for non-existent file...")
        
        try:
            nonexistent_path = os.path.join(self.temp_dir, "nonexistent.txt")
            
            # Get file size
            size = self.repo.get_file_size(nonexistent_path)
            
            if size is not None:
                print(f"    ✗ get_file_size should return None for non-existent file, got {size}")
                return False
            
            print("    ✓ Non-existent file size returns None")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def test_get_file_size_for_empty_file(self) -> bool:
        """Test get_file_size returns 0 for empty file."""
        print("  Testing get_file_size for empty file...")
        
        try:
            # Create empty file
            source_path = self._create_temp_file("")
            dest_path = os.path.join(self.temp_dir, "empty_file.txt")
            self.test_files.append(dest_path)
            self.repo.save_file(source_path, dest_path)
            
            # Get file size
            size = self.repo.get_file_size(dest_path)
            
            if size is None:
                print("    ✗ get_file_size should return 0 for empty file, not None")
                return False
            
            if size != 0:
                print(f"    ✗ Empty file size should be 0, got {size}")
                return False
            
            print("    ✓ Empty file size correct: 0 bytes")
            return True
            
        except Exception as e:
            print(f"    ✗ Test failed with exception: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all contract tests."""
        print("\nFileStorageRepository Contract Tests")
        print("=" * 60)
        
        tests = [
            ("save_file basic", self.test_save_file_basic),
            ("save_file nested directories", self.test_save_file_with_nested_directories),
            ("save_file binary", self.test_save_file_binary),
            ("save_file non-existent source", self.test_save_file_nonexistent_source),
            ("delete_file basic", self.test_delete_file_basic),
            ("delete_file directory", self.test_delete_file_directory),
            ("delete_file idempotent", self.test_delete_file_idempotent),
            ("file_exists existing file", self.test_file_exists_for_existing_file),
            ("file_exists non-existent", self.test_file_exists_for_nonexistent_file),
            ("file_exists directory", self.test_file_exists_for_directory),
            ("get_file_size file", self.test_get_file_size_for_file),
            ("get_file_size binary", self.test_get_file_size_for_binary_file),
            ("get_file_size non-existent", self.test_get_file_size_for_nonexistent_file),
            ("get_file_size empty file", self.test_get_file_size_for_empty_file),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                self.setup()
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"    ✗ Test '{test_name}' failed with exception: {e}")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))
            finally:
                self.cleanup()
        
        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✓" if result else "✗"
            print(f"  {status} {test_name}")
        
        print("=" * 60)
        print(f"FileStorageRepository Tests: {passed}/{total} passed")
        
        return all(result for _, result in results)


def test_local_file_storage_implementation():
    """Test LocalFileStorageRepository implementation against contract."""
    print("\n" + "=" * 60)
    print("Testing LocalFileStorageRepository Implementation")
    print("=" * 60)
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_base:
        repo = LocalFileStorageRepository(temp_base)
        tests = FileStorageRepositoryContractTests(repo, test_prefix="contract_test")
        return tests.run_all_tests()


def main():
    """Run all FileStorageRepository contract tests."""
    print("=" * 60)
    print("FileStorageRepository Contract Test Suite")
    print("=" * 60)
    print("\nThese tests verify that FileStorageRepository implementations")
    print("follow the contract defined by the abstract interface.")
    print("Any new implementation (GCS, S3, etc.) should pass these tests.")
    
    try:
        success = test_local_file_storage_implementation()
        
        print("\n" + "=" * 60)
        if success:
            print("✓ All FileStorageRepository contract tests passed")
            print("=" * 60)
            print("\nThis contract test suite can be reused for:")
            print("  - GCS FileStorageRepository implementation")
            print("  - S3 FileStorageRepository implementation")
            print("  - Any other storage backend implementation")
            print("\nTo test a new implementation, import it and call:")
            print("  tests = FileStorageRepositoryContractTests(your_repo)")
            print("  tests.run_all_tests()")
            return 0
        else:
            print("✗ Some FileStorageRepository contract tests failed")
            print("=" * 60)
            return 1
    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
