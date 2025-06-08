import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, jsonify
import pymysql
from your_app_module import app  # 替换为你的实际模块名

class TestFlatnessHistoryApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    # 辅助方法 - 模拟数据库返回结果
    def _mock_db_connection(self, mock_connect, mock_results=None, single_result=False):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        if mock_results is not None:
            if single_result:
                mock_cursor.fetchone.return_value = mock_results
            else:
                mock_cursor.fetchall.return_value = mock_results
        return mock_conn, mock_cursor

    # 测试历史记录查询
    @patch('your_app_module.pymysql.connect')
    def test_find_by_userName_success(self, mock_connect):
        # 模拟数据库返回
        mock_results = [
            {
                'user_name': 'test_user',
                'input_url': 'input.jpg',
                'output_id': '123',
                'output_result_url': 'output.jpg',
                'result': '合格',
                'timestamp': '2023-01-01 12:00:00'
            }
        ]
        self._mock_db_connection(mock_connect, mock_results)
        
        from your_app_module import find_by_userName
        result = find_by_userName('test_user')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['userName'], 'test_user')
        self.assertEqual(result[0]['inputImg'], 'input.jpg')
        mock_connect.assert_called_once()

    @patch('your_app_module.pymysql.connect')
    def test_find_by_userName_empty(self, mock_connect):
        # 模拟空结果
        self._mock_db_connection(mock_connect, [])
        
        from your_app_module import find_by_userName
        result = find_by_userName('nonexistent_user')
        
        self.assertEqual(result, [])
        mock_connect.assert_called_once()

    @patch('your_app_module.pymysql.connect')
    def test_find_by_userName_exception(self, mock_connect):
        # 模拟数据库异常
        mock_connect.side_effect = Exception("DB Error")
        
        from your_app_module import find_by_userName
        result = find_by_userName('test_user')
        
        self.assertEqual(result, None)

    # 测试输出ID查询
    @patch('your_app_module.pymysql.connect')
    def test_find_by_output_id_success(self, mock_connect):
        mock_results = [
            {
                'output_url': 'output.jpg',
                'edge_image_url': 'edge.jpg',
                'line_image_url': 'line.jpg',
                'gradient_image_url': 'gradient.jpg',
                'frequency_image_url': 'frequency.jpg',
                'edge_analysis': 'edge analysis',
                'line_analysis': 'line analysis',
                'gradient_analysis': 'gradient analysis',
                'frequency_analysis': 'frequency analysis'
            }
        ]
        self._mock_db_connection(mock_connect, mock_results)
        
        from your_app_module import find_by_output_id
        result = find_by_output_id('123')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['outputUrl'], 'output.jpg')
        self.assertEqual(len(result[0]['analyses']), 4)
        mock_connect.assert_called_once()

    @patch('your_app_module.pymysql.connect')
    def test_find_by_output_id_empty(self, mock_connect):
        self._mock_db_connection(mock_connect, [])
        
        from your_app_module import find_by_output_id
        result = find_by_output_id('nonexistent_id')
        
        self.assertEqual(result, [])
        mock_connect.assert_called_once()

    # 测试API端点
    def test_get_history_no_username(self):
        response = self.app.get('/flatness/history')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'No username provided', response.data)

    @patch('your_app_module.find_by_userName')
    def test_get_history_success(self, mock_find):
        mock_find.return_value = [{'userName': 'test_user', 'inputImg': 'input.jpg'}]
        
        response = self.app.get('/flatness/history?username=test_user')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'test_user', response.data)
        mock_find.assert_called_once_with('test_user')

    @patch('your_app_module.find_by_userName')
    def test_get_history_not_found(self, mock_find):
        mock_find.return_value = []
        
        response = self.app.get('/flatness/history?username=nonexistent')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'not found', response.data)

    def test_get_detail_no_params(self):
        response = self.app.get('/flatness/getDetail')
        self.assertEqual(response.status_code, 400)

    @patch('your_app_module.find_by_output_id')
    def test_get_detail_success(self, mock_find):
        mock_find.return_value = [{
            'outputUrl': 'output.jpg',
            'analyses': [{'url': 'edge.jpg', 'analysis': 'edge analysis'}]
        }]
        
        response = self.app.get('/flatness/getDetail?username=test&outputId=123')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'output.jpg', response.data)
        mock_find.assert_called_once_with('123')

if __name__ == '__main__':
    unittest.main()