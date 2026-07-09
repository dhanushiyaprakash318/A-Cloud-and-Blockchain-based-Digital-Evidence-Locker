import React, { useEffect, useRef, useState } from 'react';
import { Layout } from '@/components/layout/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageSquare, Send, Bot, User, Sparkles } from 'lucide-react';
import { assistant, cases } from '@/services/api';
import { Case } from '@/types/case';
import { cn } from '@/lib/utils';

interface AssistantChatResponse {
  answer?: string;
  message?: string;
  [key: string]: unknown;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const suggestedQuestions = [
  'How many cases are under investigation?',
  'Show me cases from Central Delhi',
  'What is the most common crime type?',
  'List all absconding accused',
  'Summarize case CR-2024-001',
];

const mockResponses: Record<string, string> = {
  'how many cases are under investigation': 
    'Currently, there are 2 cases under investigation:\n\n1. **CR-2024-001** - Cyber fraud case in Central Delhi\n2. **CR-2024-003** - Financial fraud case in North Delhi\n\nBoth cases are being actively investigated by their respective units.',
  'show me cases from central delhi':
    'Found 1 case from Central Delhi:\n\n**CR-2024-001**\n- Unit: Cyber Crime Unit\n- Status: Under Investigation\n- Date of Offence: January 15, 2024\n- Accused: Rajesh Kumar (Arrested)\n\nThis case involves alleged cyber fraud through fake e-commerce websites.',
  'what is the most common crime type':
    'Based on the current case data, the crime types are distributed as follows:\n\n- Cyber Crime: 1 case\n- Narcotics: 1 case\n- Economic Offences: 1 case\n- Violent Crime: 1 case\n- Corruption: 1 case\n\nCurrently, no single crime type dominates the database.',
  'list all absconding accused':
    'There is 1 absconding accused in the system:\n\n**Vikram Malhotra**\n- Case: CR-2024-003 (Economic Offences)\n- Age: 45, Male\n- Last Known Address: 156, Civil Lines, Delhi\n- Mobile: 9988776655\n\nPlease coordinate with the concerned unit for apprehension.',
  default:
    'I understand your query. Let me search through the case database for relevant information.\n\nBased on the available data, I can help you with:\n- Case summaries and details\n- Accused information\n- Crime statistics\n- Location-based analysis\n\nPlease try asking a specific question about cases, accused persons, or crime patterns.',
};

const Chatbot: React.FC = () => {
  const [casesList, setCasesList] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [selectedCaseMeta, setSelectedCaseMeta] = useState<Case | null>(null);
  const [caseMetaLoading, setCaseMetaLoading] = useState(false);
  const [caseMetaError, setCaseMetaError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your AI assistant for the Case Management System. Select a case and ask a question to get answers from case evidence and summaries.',
      timestamp: new Date(),
    },
  ]);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [loadingCases, setLoadingCases] = useState(false);
  const [caseFetchError, setCaseFetchError] = useState<string | null>(null);

  useEffect(() => {
    const loadCases = async () => {
      setLoadingCases(true);
      try {
        const response = await cases.list();
        const list = response.cases || [];
        setCasesList(list);
        if (list.length > 0) {
          setSelectedCaseId((value) => value || list[0].id);
        }
      } catch (error) {
        setCaseFetchError('Unable to load cases. Please try again later.');
      } finally {
        setLoadingCases(false);
      }
    };

    loadCases();

    // Load persisted chat from sessionStorage for this browser session
    try {
      const saved = sessionStorage.getItem('divel_chat_history');
      const savedCase = sessionStorage.getItem('divel_chat_case');
      if (savedCase) setSelectedCaseId(savedCase);
      if (saved) {
        try {
          const rawParsed = JSON.parse(saved) as unknown;
          if (Array.isArray(rawParsed)) {
            const parsed: Message[] = rawParsed.map((m) => {
              const item = m as Record<string, unknown>;
              const id = typeof item.id === 'string' ? item.id : Date.now().toString();
              const role = item.role === 'user' || item.role === 'assistant' ? (item.role as 'user' | 'assistant') : 'assistant';
              const content = typeof item.content === 'string' ? item.content : '';
              const timestamp = typeof item.timestamp === 'string' ? new Date(item.timestamp) : new Date();
              return { id, role, content, timestamp } as Message;
            });
            if (parsed && parsed.length > 0) setMessages(parsed);
          }
        } catch (e) {
          // ignore JSON parse errors
        }
      }
    } catch (e) {
      // ignore session load errors
    }
  }, []);

  // Load case metadata when selectedCaseId changes
  useEffect(() => {
    const loadCaseMeta = async (id: string) => {
      setCaseMetaLoading(true);
      setCaseMetaError(null);
      try {
        const resp = await cases.get(id);
        // resp shape: { case: ... } or the case object depending on API
        const data = (resp && (resp.case || resp)) as Case;
        setSelectedCaseMeta(data || null);
      } catch (err) {
        setCaseMetaError('Unable to load case details.');
        setSelectedCaseMeta(null);
      } finally {
        setCaseMetaLoading(false);
      }
    };

    if (selectedCaseId) {
      loadCaseMeta(selectedCaseId);
    } else {
      setSelectedCaseMeta(null);
      setCaseMetaError(null);
    }
  }, [selectedCaseId]);

  const handleSend = async () => {
    if (!input.trim()) return;

    if (!selectedCaseId) {
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Please select a case before asking a question.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await assistant.chat(selectedCaseId, input) as AssistantChatResponse;
      const raw = response.answer ?? response.message ?? '';

      const assistantContent = formatAssistantAnswer(raw);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: assistantContent || 'I cannot find this information in the uploaded evidence.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Sorry, I couldn't process your request. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  // Persist chat history and selected case during the browser session
  useEffect(() => {
    try {
      sessionStorage.setItem('divel_chat_history', JSON.stringify(messages.map(m => ({ ...m, timestamp: m.timestamp.toISOString() }))));
      if (selectedCaseId) sessionStorage.setItem('divel_chat_case', selectedCaseId);
    } catch (e) {
      // ignore storage errors
    }
    // Scroll to bottom on messages change
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages, selectedCaseId]);

  function formatAssistantAnswer(raw: unknown): string {
    if (raw === undefined || raw === null) return '';
    if (typeof raw === 'string') return raw;
    if (typeof raw === 'number') return String(raw);
    if (Array.isArray(raw)) {
      if (raw.length === 0) return '';
      // Pretty-print an array of objects or strings
      return raw.map((item, idx) => {
        if (typeof item === 'string') return `${idx + 1}. ${item}`;
        if (typeof item === 'number') return `${idx + 1}. ${item}`;
        if (typeof item === 'object' && item !== null) {
          const obj = item as Record<string, unknown>;
          // compact summary for case search results
          if (obj.caseNumber || obj.caseId) {
            const id = (obj.caseNumber as string) || (obj.caseId as string) || (obj.id as string) || 'unknown';
            const district = (obj.district as string) || (obj.location as string) || '';
            const status = (obj.status as string) || '';
            const date = (obj.dateOfOffence as string) || (obj.date as string) || '';
            return `${idx + 1}. ${id} — ${district} — ${status} ${date ? '- ' + date : ''}`.trim();
          }
          // otherwise list key: value
          return (
            `${idx + 1}. ` + Object.entries(obj).map(([k, v]) => `${capitalize(k)}: ${String(v)}`).join(' | ')
          );
        }
        return `${idx + 1}. ${String(item)}`;
      }).join('\n\n');
    }
    if (typeof raw === 'object') {
      const obj = raw as Record<string, unknown>;
      return Object.entries(obj).map(([k, v]) => `${capitalize(k)}: ${String(v)}`).join('\n');
    }
    return String(raw);
  }

  function capitalize(s: string) {
    if (!s) return s;
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function escapeHtml(unsafe: string) {
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function renderMessageContent(message: Message, idx: number) {
    const raw = message.content || '';
    // If assistant returned a pure number and previous user asked 'how many', render a friendly sentence
    if (message.role === 'assistant' && /^\s*\d+\s*$/.test(raw)) {
      // find previous user message
      const prevUser = [...messages].slice(0, idx).reverse().find((m) => m.role === 'user');
      if (prevUser && /how many|count|total|how many cases/i.test(prevUser.content)) {
        const n = raw.trim();
        return <span dangerouslySetInnerHTML={{ __html: `Total cases: <strong>${escapeHtml(n)}</strong>` }} />;
      }
    }

    // Basic safe markdown: **bold**, *italic* and preserve line breaks
    let html = escapeHtml(String(raw));
    // bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // convert lines to <br />
    html = html.replace(/\r?\n/g, '<br/>');

    return <span dangerouslySetInnerHTML={{ __html: html }} />;
  }

  const handleSuggestedQuestion = (question: string) => {
    setInput(question);
  };

  return (
    <Layout>
      <div className="container py-8">
        <div className="max-w-6xl mx-auto space-y-6">
          <div>
            <h1 className="text-3xl font-bold">AI Assistant</h1>
            <p className="text-muted-foreground mt-1">
              Ask questions about cases, accused persons, and crime patterns
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,3fr)_1fr] gap-6">
            {/* Chat Area */}
            <Card className="flex flex-col min-h-[680px]">
              <CardHeader className="flex flex-col gap-3">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <CardTitle>Case-aware AI Chat</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Ask questions and get answers based on a selected case's evidence.
                    </p>
                  </div>
                  <div className="mt-3 sm:mt-0">
                    {caseMetaLoading ? (
                      <p className="text-sm text-muted-foreground">Loading case details...</p>
                    ) : caseMetaError ? (
                      <p className="text-sm text-destructive">{caseMetaError}</p>
                    ) : selectedCaseMeta ? (
                      <div className="text-sm text-muted-foreground text-right">
                        <div><strong>Case Number:</strong> {selectedCaseMeta.caseNumber || selectedCaseMeta.id}</div>
                        <div><strong>Status:</strong> {selectedCaseMeta.status || 'Unknown'}</div>
                        <div><strong>District:</strong> {selectedCaseMeta.district || selectedCaseMeta.location || 'Unknown'}</div>
                        <div><strong>Date Reported:</strong> {selectedCaseMeta.dateOfReport || selectedCaseMeta.dateOfOffence || 'Unknown'}</div>
                        <div><strong>Evidence Files:</strong> {(selectedCaseMeta.evidence || []).length}</div>
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No case selected.</p>
                    )}
                  </div>
                  <div className="space-y-2 sm:space-y-0 sm:flex sm:items-center sm:gap-2">
                    <Select value={selectedCaseId} onValueChange={setSelectedCaseId} disabled={casesList.length === 0}>
                      <SelectTrigger className="min-w-[220px]">
                        <SelectValue placeholder={loadingCases ? 'Loading cases...' : 'Select a case'} />
                      </SelectTrigger>
                      <SelectContent>
                        {casesList.map((caseItem) => (
                          <SelectItem key={caseItem.id} value={caseItem.id}>
                            {caseItem.caseNumber} — {caseItem.district}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {caseFetchError && <p className="text-xs text-destructive">{caseFetchError}</p>}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-0 flex flex-col min-h-[680px]">
                {/* Messages */}
                <ScrollArea className="flex-1 p-4 overflow-hidden min-h-0">
                  <div className="space-y-4 min-h-full">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={cn(
                          'flex gap-3',
                          message.role === 'user' ? 'justify-end' : 'justify-start'
                        )}
                      >
                        {message.role === 'assistant' && (
                          <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                            <Bot className="h-4 w-4 text-primary-foreground" />
                          </div>
                        )}
                        <div
                          className={cn(
                            'rounded-lg px-4 py-3 max-w-[80%]',
                            message.role === 'user'
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-muted'
                          )}
                        >
                          {message.role === 'assistant' && message.content.includes('Case Number:') ? (
                            message.content
                              .split(/\n\s*\n(?=Case Number:)/)
                              .map((block, i) => (
                                <div key={i} className="bg-background p-3 rounded-md mb-3">
                                  {block.split('\n').map((line, j) => (
                                    <div key={j} className="text-sm whitespace-pre-wrap">{line}</div>
                                  ))}
                                </div>
                              ))
                          ) : (
                            <>
                              <div className="text-sm">
                                {renderMessageContent(message, messages.findIndex((m) => m.id === message.id))}
                              </div>
                              <p
                                className={cn(
                                  'text-xs mt-2',
                                  message.role === 'user'
                                    ? 'text-primary-foreground/70'
                                    : 'text-muted-foreground'
                                )}
                              >
                                {message.timestamp.toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </p>
                            </>
                          )}
                        </div>
                        {message.role === 'user' && (
                          <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
                            <User className="h-4 w-4" />
                          </div>
                        )}
                      </div>
                    ))}

                    {isTyping && (
                      <div className="flex gap-3">
                        <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                          <Bot className="h-4 w-4 text-primary-foreground" />
                        </div>
                        <div className="bg-muted rounded-lg px-4 py-3">
                          <div className="flex gap-1">
                            <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" />
                            <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce delay-200" />
                            <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce delay-400" />
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={bottomRef} />
                  </div>
                </ScrollArea>

                {/* Input */}
                <div className="p-4 border-t border-border">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleSend();
                    }}
                    className="flex gap-2 flex-col md:flex-row"
                  >
                    <Input
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder={selectedCaseId ? 'Ask a question about the selected case...' : 'Select a case first'}
                      className="flex-1"
                      disabled={!selectedCaseId}
                    />
                    <Button type="submit" disabled={!input.trim() || isTyping || !selectedCaseId}>
                      <Send className="h-4 w-4" />
                    </Button>
                  </form>
                </div>
              </CardContent>
            </Card>

            {/* Suggested Questions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="h-5 w-5" />
                  Suggested
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {suggestedQuestions.map((question, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      className="w-full justify-start text-left h-auto py-2 px-3"
                      onClick={() => handleSuggestedQuestion(question)}
                    >
                      <MessageSquare className="h-3 w-3 mr-2 shrink-0" />
                      <span className="text-xs">{question}</span>
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Chatbot;