'use client'

import { useState } from 'react'
import {
  Box,
  Button,
  Container,
  FormControl,
  FormLabel,
  Input,
  VStack,
  Text,
  useToast,
  Alert,
  AlertIcon,
} from '@chakra-ui/react'
import { useRouter } from 'next/navigation'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const router = useRouter()
  const toast = useToast()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      console.log('ログイン試行中...')
      console.log('リクエスト先URL:', '/api/auth/login')
      
      // Next.jsのAPIルートを使用
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)
      
      console.log('送信データ:', {
        username,
        password: '***'
      })
      
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: formData,
      })

      console.log('レスポンスステータス:', response.status)
      
      // レスポンスのテキストを取得
      const responseText = await response.text()
      console.log('レスポンス本文:', responseText)
      
      // JSONとして解析
      let data
      try {
        data = JSON.parse(responseText)
        console.log('ログインレスポンス:', data)
      } catch (e) {
        console.error('JSONパースエラー:', e)
        throw new Error('レスポンスの解析に失敗しました')
      }

      if (response.ok && data.access_token) {
        // トークンを保存
        localStorage.setItem('token', data.access_token)
        // ユーザー情報を保存
        localStorage.setItem('user', JSON.stringify(data.user))
        
        toast({
          title: 'ログイン成功',
          status: 'success',
          duration: 3000,
          isClosable: true,
        })
        
        router.push('/dashboard')
      } else if (response.status === 401) {
        throw new Error('ユーザー名またはパスワードが間違っています')
      } else if (data.detail === 'Not Found') {
        throw new Error('APIエンドポイントが見つかりません')
      } else {
        throw new Error(data.detail || 'ログインに失敗しました')
      }
    } catch (error) {
      console.error('ログインエラー:', error)
      setError(error instanceof Error ? error.message : 'ログインに失敗しました')
      toast({
        title: 'ログイン失敗',
        description: error instanceof Error ? error.message : 'ログインに失敗しました',
        status: 'error',
        duration: 3000,
        isClosable: true,
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Container maxW="container.sm" py={10}>
      <VStack spacing={8}>
        <Text fontSize="2xl" fontWeight="bold">
          管理者ログイン
        </Text>
        
        {error && (
          <Alert status="error">
            <AlertIcon />
            {error}
          </Alert>
        )}
        
        <Box w="100%" p={8} borderWidth={1} borderRadius="lg">
          <form onSubmit={handleLogin}>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>ユーザー名</FormLabel>
                <Input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isLoading}
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel>パスワード</FormLabel>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
              </FormControl>
              <Button
                type="submit"
                colorScheme="blue"
                width="100%"
                isLoading={isLoading}
                loadingText="ログイン中..."
              >
                ログイン
              </Button>
            </VStack>
          </form>
        </Box>
        <Text fontSize="sm" color="gray.500">
          API URL: /api/auth/login → http://localhost:8000/auth/login
        </Text>
      </VStack>
    </Container>
  )
} 