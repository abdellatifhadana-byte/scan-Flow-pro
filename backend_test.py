#!/usr/bin/env python3
"""
ScanFlow Pro Backend Testing Suite
Complete end-to-end testing as requested in Arabic instructions
"""

import requests
import json
import time
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BACKEND_URL = "https://scanflow-pro.preview.emergentagent.com/api"
UPLOADS_DIR = Path("/app/backend/uploads")
TEST_PDF_PATH = UPLOADS_DIR / "1210cd86-98cd-46b5-b01d-40eee6aa10a7.pdf"

class ScanFlowTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.file_id = None
        self.analysis_id = None
        
    def test_api_health(self):
        """Test if API is accessible"""
        logger.info("🔍 Testing API health...")
        try:
            response = self.session.get(f"{BACKEND_URL}/")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ API is healthy: {data}")
                return True
            else:
                logger.error(f"❌ API health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ API connection failed: {str(e)}")
            return False
    
    def test_upload_pdf(self):
        """Test PDF upload - POST /api/upload"""
        logger.info("📤 Testing PDF upload...")
        
        if not TEST_PDF_PATH.exists():
            logger.error(f"❌ Test PDF not found at {TEST_PDF_PATH}")
            return False
            
        try:
            # Remove Content-Type header for file upload
            headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
            
            with open(TEST_PDF_PATH, 'rb') as f:
                files = {'file': ('test_document.pdf', f, 'application/pdf')}
                response = requests.post(f"{BACKEND_URL}/upload", files=files, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.file_id = data['file_id']
                logger.info(f"✅ PDF uploaded successfully:")
                logger.info(f"   File ID: {self.file_id}")
                logger.info(f"   Filename: {data['filename']}")
                logger.info(f"   Page count: {data['page_count']}")
                logger.info(f"   Size: {data['size']} bytes")
                return True
            else:
                logger.error(f"❌ Upload failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Upload error: {str(e)}")
            return False
    
    def test_set_file_config(self):
        """Test file configuration - POST /api/files/{file_id}/config"""
        logger.info("⚙️ Testing file configuration...")
        
        if not self.file_id:
            logger.error("❌ No file_id available for configuration")
            return False
            
        config_data = {
            "file_id": self.file_id,
            "keyword": "Code",
            "nom": "TEST",
            "code_roi": {
                "x": 0.1,
                "y": 0.1,
                "width": 0.8,
                "height": 0.2
            },
            "rotation": 0,
            "pages_per_code": 1,
            "auto_detect": False
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/files/{self.file_id}/config",
                json=config_data
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Configuration saved: {data['message']}")
                return True
            else:
                logger.error(f"❌ Configuration failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Configuration error: {str(e)}")
            return False
    
    def test_start_analysis(self):
        """Test analysis start - POST /api/analyze"""
        logger.info("🔬 Testing analysis start...")
        
        if not self.file_id:
            logger.error("❌ No file_id available for analysis")
            return False
            
        analysis_data = {
            "file_ids": [self.file_id],
            "merge_enabled": True
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/analyze",
                json=analysis_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.analysis_id = data['analysis_id']
                logger.info(f"✅ Analysis started:")
                logger.info(f"   Analysis ID: {self.analysis_id}")
                logger.info(f"   Message: {data['message']}")
                return True
            else:
                logger.error(f"❌ Analysis start failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Analysis start error: {str(e)}")
            return False
    
    def test_analysis_status(self, max_wait_time=120):
        """Test analysis status monitoring - GET /api/analysis/{analysis_id}"""
        logger.info("⏳ Testing analysis status monitoring...")
        
        if not self.analysis_id:
            logger.error("❌ No analysis_id available")
            return False
            
        start_time = time.time()
        
        try:
            while time.time() - start_time < max_wait_time:
                response = self.session.get(f"{BACKEND_URL}/analysis/{self.analysis_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    progress = data.get('progress', 0)
                    
                    logger.info(f"   Status: {status}, Progress: {progress}%")
                    
                    if status == 'completed':
                        logger.info("✅ Analysis completed successfully!")
                        return True
                    elif status == 'failed':
                        error = data.get('error', 'Unknown error')
                        logger.error(f"❌ Analysis failed: {error}")
                        return False
                    elif status in ['processing', 'extracting', 'aligning', 'grouping', 'creating_files']:
                        # Continue monitoring
                        time.sleep(3)
                        continue
                    else:
                        logger.warning(f"⚠️ Unknown status: {status}")
                        time.sleep(3)
                        continue
                else:
                    logger.error(f"❌ Status check failed: {response.status_code} - {response.text}")
                    return False
            
            logger.error(f"❌ Analysis timeout after {max_wait_time} seconds")
            return False
            
        except Exception as e:
            logger.error(f"❌ Status monitoring error: {str(e)}")
            return False
    
    def test_get_results(self):
        """Test results retrieval - GET /api/analysis/{analysis_id}"""
        logger.info("📊 Testing results retrieval...")
        
        if not self.analysis_id:
            logger.error("❌ No analysis_id available")
            return False
            
        try:
            response = self.session.get(f"{BACKEND_URL}/analysis/{self.analysis_id}")
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                logger.info(f"✅ Results retrieved successfully:")
                logger.info(f"   Total results: {len(results)}")
                
                if results:
                    for i, result in enumerate(results[:3]):  # Show first 3 results
                        logger.info(f"   Result {i+1}:")
                        logger.info(f"     - Source filename: {result.get('source_filename', 'N/A')}")
                        logger.info(f"     - Code: {result.get('code', 'N/A')}")
                        logger.info(f"     - Aligned code: {result.get('aligned_code', 'N/A')}")
                        logger.info(f"     - Confidence: {result.get('confidence', 0)}%")
                        logger.info(f"     - NOM: {result.get('nom', 'N/A')}")
                        logger.info(f"     - Page count: {result.get('page_count', 0)}")
                    
                    # Verify required fields are present
                    required_fields = ['source_filename', 'code', 'confidence', 'nom']
                    missing_fields = []
                    
                    for field in required_fields:
                        if not any(field in result for result in results):
                            missing_fields.append(field)
                    
                    if missing_fields:
                        logger.warning(f"⚠️ Missing required fields in results: {missing_fields}")
                    else:
                        logger.info("✅ All required fields present in results")
                    
                    return True
                else:
                    logger.warning("⚠️ No results found in analysis")
                    return False
            else:
                logger.error(f"❌ Results retrieval failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Results retrieval error: {str(e)}")
            return False
    
    def test_additional_endpoints(self):
        """Test additional endpoints for completeness"""
        logger.info("🔍 Testing additional endpoints...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test get files
        total_tests += 1
        try:
            response = self.session.get(f"{BACKEND_URL}/files")
            if response.status_code == 200:
                files = response.json()
                logger.info(f"✅ GET /files: Found {len(files)} files")
                tests_passed += 1
            else:
                logger.error(f"❌ GET /files failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ GET /files error: {str(e)}")
        
        # Test get keywords
        total_tests += 1
        try:
            response = self.session.get(f"{BACKEND_URL}/keywords")
            if response.status_code == 200:
                keywords = response.json()
                logger.info(f"✅ GET /keywords: Found {len(keywords)} keywords")
                tests_passed += 1
            else:
                logger.error(f"❌ GET /keywords failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ GET /keywords error: {str(e)}")
        
        # Test file config retrieval if we have a file_id
        if self.file_id:
            total_tests += 1
            try:
                response = self.session.get(f"{BACKEND_URL}/files/{self.file_id}/config")
                if response.status_code == 200:
                    config = response.json()
                    logger.info(f"✅ GET /files/{self.file_id}/config: Retrieved config")
                    tests_passed += 1
                else:
                    logger.error(f"❌ GET /files/{self.file_id}/config failed: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ GET /files/{self.file_id}/config error: {str(e)}")
        
        logger.info(f"📈 Additional tests: {tests_passed}/{total_tests} passed")
        return tests_passed == total_tests
    
    def run_complete_test(self):
        """Run complete end-to-end test suite"""
        logger.info("🚀 Starting ScanFlow Pro Complete Backend Test")
        logger.info("=" * 60)
        
        test_results = {}
        
        # Test 1: API Health
        test_results['api_health'] = self.test_api_health()
        
        # Test 2: PDF Upload
        test_results['upload'] = self.test_upload_pdf()
        
        # Test 3: File Configuration
        test_results['config'] = self.test_set_file_config()
        
        # Test 4: Start Analysis
        test_results['start_analysis'] = self.test_start_analysis()
        
        # Test 5: Monitor Analysis Status
        test_results['analysis_status'] = self.test_analysis_status()
        
        # Test 6: Get Results
        test_results['get_results'] = self.test_get_results()
        
        # Test 7: Additional Endpoints
        test_results['additional'] = self.test_additional_endpoints()
        
        # Summary
        logger.info("=" * 60)
        logger.info("📋 TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name.upper()}: {status}")
        
        logger.info("=" * 60)
        logger.info(f"OVERALL RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED! ScanFlow Pro backend is working correctly.")
            return True
        else:
            logger.error(f"⚠️ {total - passed} tests failed. Backend needs attention.")
            return False

def main():
    """Main test execution"""
    tester = ScanFlowTester()
    success = tester.run_complete_test()
    
    if success:
        print("\n🎯 CONCLUSION: Backend APIs are working correctly!")
        print("✅ The system can successfully:")
        print("   - Upload PDF files")
        print("   - Configure file settings with ROI")
        print("   - Start OCR analysis")
        print("   - Monitor analysis progress")
        print("   - Retrieve analysis results with extracted codes")
        return 0
    else:
        print("\n❌ CONCLUSION: Backend has issues that need to be addressed!")
        return 1

if __name__ == "__main__":
    exit(main())