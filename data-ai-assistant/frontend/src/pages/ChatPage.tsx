import React, { useState, useRef, useEffect } from 'react';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  List,
  ListItem,
  Alert,
  CircularProgress,
  Chip,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import { Send, Psychology, Code, TableChart } from '@mui/icons-material';
import { queryApi, QueryResponse } from '../services/api';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  data?: QueryResponse;
}

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // 컴포넌트 마운트 시 지식 베이스 초기화
    initializeKnowledgeBase();
  }, []);

  const initializeKnowledgeBase = async () => {
    try {
      await queryApi.initialize();
      setIsInitialized(true);
      addMessage('assistant', '지식 베이스가 초기화되었습니다. 이제 질문을 해보세요!');
    } catch (error) {
      console.error('Knowledge base initialization failed:', error);
      addMessage('assistant', '지식 베이스 초기화에 실패했습니다. 다시 시도해주세요.');
    }
  };

  const addMessage = (type: 'user' | 'assistant', content: string, data?: QueryResponse) => {
    const message: Message = {
      id: Date.now().toString(),
      type,
      content,
      timestamp: new Date(),
      data,
    };
    setMessages(prev => [...prev, message]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    addMessage('user', userMessage);
    setLoading(true);

    try {
      const response = await queryApi.ask({ question: userMessage });
      addMessage('assistant', response.answer, response);
    } catch (error: any) {
      addMessage('assistant', `오류가 발생했습니다: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const renderDataTable = (data: any[], columns: string[]) => {
    if (!data || data.length === 0) return null;

    return (
      <TableContainer component={Paper} sx={{ mt: 2, maxHeight: 400 }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell key={column} sx={{ fontWeight: 'bold' }}>
                  {column}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((row, index) => (
              <TableRow key={index}>
                {columns.map((column) => (
                  <TableCell key={column}>
                    {row[column]?.toString() || ''}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  const renderMessage = (message: Message) => {
    const isUser = message.type === 'user';
    
    return (
      <ListItem
        key={message.id}
        sx={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          mb: 1,
        }}
      >
        <Box
          sx={{
            maxWidth: '80%',
            p: 2,
            borderRadius: 2,
            bgcolor: isUser ? 'primary.main' : 'grey.100',
            color: isUser ? 'white' : 'text.primary',
          }}
        >
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
            {message.content}
          </Typography>
          
          {message.data && (
            <Box sx={{ mt: 2 }}>
              {message.data.success && (
                <Chip
                  icon={<Psychology />}
                  label="답변 성공"
                  color="success"
                  size="small"
                  sx={{ mb: 1 }}
                />
              )}
              
              {message.data.confidence && (
                <Chip
                  label={`신뢰도: ${Math.round(message.data.confidence * 100)}%`}
                  color="info"
                  size="small"
                  sx={{ mb: 1, ml: 1 }}
                />
              )}
              
              {message.data.sql_query && (
                <Card sx={{ mt: 2 }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Code sx={{ mr: 1 }} />
                      <Typography variant="subtitle2">생성된 SQL 쿼리</Typography>
                    </Box>
                    <Paper sx={{ p: 1, bgcolor: 'grey.50' }}>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {message.data.sql_query}
                      </Typography>
                    </Paper>
                  </CardContent>
                </Card>
              )}
              
              {message.data.data && message.data.columns && (
                <Card sx={{ mt: 2 }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <TableChart sx={{ mr: 1 }} />
                      <Typography variant="subtitle2">
                        쿼리 결과 ({message.data.row_count}개 행)
                      </Typography>
                    </Box>
                    {renderDataTable(message.data.data, message.data.columns)}
                  </CardContent>
                </Card>
              )}
              
              {message.data.error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {message.data.error}
                </Alert>
              )}
            </Box>
          )}
          
          <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.7 }}>
            {message.timestamp.toLocaleTimeString()}
          </Typography>
        </Box>
      </ListItem>
    );
  };

  const sampleQuestions = [
    "모든 고객 목록을 보여주세요",
    "총 주문 금액이 가장 높은 고객은 누구인가요?",
    "카테고리별 제품 수를 알려주세요",
    "재고가 부족한 제품을 찾아주세요",
  ];

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Data AI Assistant
      </Typography>
      
      {!isInitialized && (
        <Alert severity="info" sx={{ mb: 2 }}>
          지식 베이스를 초기화하는 중입니다...
        </Alert>
      )}
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ height: '60vh', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <Typography variant="h6">채팅</Typography>
            </Box>
            
            <Box sx={{ flex: 1, overflow: 'auto' }}>
              {messages.length === 0 ? (
                <Box sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    안녕하세요! 데이터에 대해 자연어로 질문해보세요.
                  </Typography>
                </Box>
              ) : (
                <List sx={{ p: 1 }}>
                  {messages.map(renderMessage)}
                  <div ref={messagesEndRef} />
                </List>
              )}
            </Box>
            
            <Divider />
            
            <Box sx={{ p: 2 }}>
              <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  variant="outlined"
                  placeholder="질문을 입력하세요..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading || !isInitialized}
                  size="small"
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={loading || !isInitialized}
                  sx={{ minWidth: 48 }}
                >
                  {loading ? <CircularProgress size={20} /> : <Send />}
                </Button>
              </Box>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              샘플 질문
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              다음 질문들을 클릭해보세요:
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {sampleQuestions.map((question, index) => (
                <Button
                  key={index}
                  variant="outlined"
                  size="small"
                  onClick={() => setInput(question)}
                  disabled={loading || !isInitialized}
                  sx={{ justifyContent: 'flex-start', textAlign: 'left' }}
                >
                  {question}
                </Button>
              ))}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default ChatPage;