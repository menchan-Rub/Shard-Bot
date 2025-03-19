'use client'

import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Center,
  VStack,
  Text,
  Heading,
  useToast,
  Icon,
  Flex,
  Container,
  Divider,
  useColorModeValue,
  SlideFade,
  ScaleFade,
  HStack,
  Badge,
} from '@chakra-ui/react'
import { FaDiscord, FaShieldAlt, FaLock, FaUserShield } from 'react-icons/fa'
import { motion } from 'framer-motion'

const MotionBox = motion(Box)

export default function Login() {
  const toast = useToast()
  const [isLoading, setIsLoading] = useState(false)
  const bgGradient = useColorModeValue(
    'linear(to-br, blue.400, purple.500)',
    'linear(to-br, blue.600, purple.700)'
  )
  const cardBg = useColorModeValue('white', 'gray.800')
  const textColor = useColorModeValue('gray.600', 'gray.200')

  const handleDiscordLogin = async () => {
    try {
      setIsLoading(true)
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
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Box 
      minH="100vh" 
      bgGradient={bgGradient}
      display="flex"
      alignItems="center"
      justifyContent="center"
      position="relative"
      overflow="hidden"
    >
      {/* 背景アニメーション要素 */}
      <MotionBox
        position="absolute"
        width="500px"
        height="500px"
        borderRadius="full"
        bgGradient="linear(to-r, blue.300, purple.400)"
        filter="blur(80px)"
        opacity="0.4"
        animate={{ 
          x: ['-20%', '10%', '-10%'],
          y: ['-10%', '15%', '-5%'],
        }}
        transition={{ 
          repeat: Infinity,
          repeatType: "reverse",
          duration: 20
        }}
        zIndex={0}
      />

      <Container maxW="md" position="relative" zIndex={1}>
        <ScaleFade initialScale={0.9} in={true}>
          <Box
            p={8}
            borderRadius="xl"
            boxShadow="xl"
            bg={cardBg}
            border="1px solid"
            borderColor="gray.100"
            _dark={{ borderColor: 'gray.700' }}
          >
            <VStack spacing={6} align="stretch">
              <Center>
                <Icon as={FaUserShield} w={16} h={16} color="purple.500" mb={2} />
              </Center>
              
              <VStack spacing={2}>
                <Heading size="xl" textAlign="center" bgGradient="linear(to-r, blue.400, purple.500)" 
                  bgClip="text">
                  Shard Bot
                </Heading>
                <Text fontSize="lg" color={textColor} textAlign="center">
                  管理ダッシュボード
                </Text>
              </VStack>
              
              <Divider />
              
              <Button
                leftIcon={<FaDiscord />}
                colorScheme="purple"
                size="lg"
                height="56px"
                fontSize="md"
                onClick={handleDiscordLogin}
                isLoading={isLoading}
                _hover={{
                  transform: 'translateY(-2px)',
                  boxShadow: 'lg',
                }}
                bgGradient="linear(to-r, purple.500, blue.500)"
              >
                Discordでログイン
              </Button>
              
              <VStack spacing={4} pt={4}>
                <HStack spacing={2}>
                  <Icon as={FaShieldAlt} color="green.500" />
                  <Text fontSize="sm" color={textColor}>安全な認証プロセス</Text>
                </HStack>
                
                <HStack spacing={2}>
                  <Icon as={FaLock} color="green.500" />
                  <Text fontSize="sm" color={textColor}>許可されたユーザーのみアクセス可能</Text>
                </HStack>
                
                <Badge colorScheme="purple" px={3} py={1}>
                  Discord OAuth2認証
                </Badge>
              </VStack>
            </VStack>
          </Box>
        </ScaleFade>
      </Container>
    </Box>
  )
} 