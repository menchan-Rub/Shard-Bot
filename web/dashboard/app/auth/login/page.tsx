'use client'

import { useEffect } from 'react'
import {
  Box,
  Button,
  Center,
  VStack,
  Text,
  useToast,
} from '@chakra-ui/react'
import { FaDiscord } from 'react-icons/fa'

export default function Login() {
  const toast = useToast()

  const handleDiscordLogin = async () => {
    try {
      // Discord認証URLを取得
      const response = await fetch('/api/auth/discord/url')
      const data = await response.json()
      
      // Discord認証ページにリダイレクト
      window.location.href = data.url
    } catch (error) {
      console.error('Discord認証URLの取得に失敗:', error)
      toast({
        title: 'エラー',
        description: 'ログインに失敗しました',
        status: 'error',
        duration: 5000,
        isClosable: true,
      })
    }
  }

  return (
    <Center minH="100vh" bg="gray.50">
      <Box
        p={8}
        maxWidth="400px"
        borderWidth={1}
        borderRadius={8}
        boxShadow="lg"
        bg="white"
      >
        <VStack spacing={4} align="stretch">
          <Text fontSize="2xl" textAlign="center" mb={4}>
            Shard Bot Dashboard
          </Text>
          
          <Button
            leftIcon={<FaDiscord />}
            colorScheme="purple"
            size="lg"
            onClick={handleDiscordLogin}
          >
            Discordでログイン
          </Button>
          
          <Text fontSize="sm" color="gray.500" textAlign="center">
            ※ 許可されたユーザーのみログインできます
          </Text>
        </VStack>
      </Box>
    </Center>
  )
} 