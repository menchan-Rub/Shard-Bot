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
} from '@chakra-ui/react'
import { useRouter } from 'next/navigation'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()
  const toast = useToast()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      console.log('Attempting login to:', 'http://localhost:8080/api/auth/login')
      
      const response = await fetch('http://localhost:8080/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: new URLSearchParams({
          username,
          password,
        }),
      })

      console.log('Response status:', response.status)
      const contentType = response.headers.get('content-type')
      console.log('Content type:', contentType)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('Error response:', errorText)
        throw new Error(`Login failed: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      console.log('Login successful:', data)
      
      // ログイン成功時の処理
      localStorage.setItem('token', data.data.access_token)
      toast({
        title: 'ログイン成功',
        status: 'success',
        duration: 3000,
        isClosable: true,
      })
      router.push('/dashboard')
    } catch (error) {
      console.error('Login error:', error)
      toast({
        title: 'ログイン失敗',
        description: error instanceof Error ? error.message : 'ユーザー名またはパスワードが間違っています',
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
          API URL: {process.env.NEXT_PUBLIC_API_URL}
        </Text>
      </VStack>
    </Container>
  )
} 