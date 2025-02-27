'use client'

import { Box, Button, Container, Heading, Text, VStack } from '@chakra-ui/react'
import { signIn } from 'next-auth/react'
import { FaDiscord } from 'react-icons/fa'

export default function SignIn() {
  return (
    <Container maxW="container.md" py={20}>
      <VStack spacing={8} align="center">
        <Heading size="2xl">Welcome to Shard Bot</Heading>
        <Text fontSize="xl">Sign in to manage your Discord bot settings</Text>
        <Box p={8}>
          <Button
            leftIcon={<FaDiscord />}
            colorScheme="purple"
            size="lg"
            onClick={() => signIn('discord', { callbackUrl: '/dashboard' })}
          >
            Sign in with Discord
          </Button>
        </Box>
      </VStack>
    </Container>
  )
} 