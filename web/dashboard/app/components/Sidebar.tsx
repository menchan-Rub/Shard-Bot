'use client'

import {
  Box,
  VStack,
  Icon,
  Link,
  Text,
  Flex,
} from '@chakra-ui/react'
import NextLink from 'next/link'
import { usePathname } from 'next/navigation'
import {
  FaHome,
  FaCog,
  FaChartBar,
  FaDiscord,
} from 'react-icons/fa'

const menuItems = [
  { name: 'Overview', icon: FaHome, path: '/dashboard' },
  { name: 'Statistics', icon: FaChartBar, path: '/dashboard/statistics' },
  { name: 'Settings', icon: FaCog, path: '/dashboard/settings' },
  { name: 'Servers', icon: FaDiscord, path: '/dashboard/servers' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <Box
      w="240px"
      bg="gray.800"
      color="white"
      h="100vh"
      py={8}
      px={4}
    >
      <VStack spacing={8} align="stretch">
        <Box px={4}>
          <Text fontSize="xl" fontWeight="bold">
            Shard Bot
          </Text>
        </Box>
        <VStack spacing={2} align="stretch">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              as={NextLink}
              href={item.path}
              _hover={{ textDecoration: 'none' }}
            >
              <Flex
                align="center"
                px={4}
                py={3}
                borderRadius="md"
                bg={pathname === item.path ? 'purple.500' : 'transparent'}
                _hover={{ bg: pathname === item.path ? 'purple.600' : 'whiteAlpha.200' }}
              >
                <Icon as={item.icon} mr={3} />
                <Text>{item.name}</Text>
              </Flex>
            </Link>
          ))}
        </VStack>
      </VStack>
    </Box>
  )
} 