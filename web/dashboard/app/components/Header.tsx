'use client'

import {
  Box,
  Flex,
  IconButton,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Text,
} from '@chakra-ui/react'
import { signOut, useSession } from 'next-auth/react'
import { FaUserCircle } from 'react-icons/fa'

export default function Header() {
  const { data: session } = useSession()

  return (
    <Box bg="white" px={8} py={4} borderBottom="1px" borderColor="gray.200">
      <Flex justify="space-between" align="center">
        <Text fontSize="xl" fontWeight="bold">
          Dashboard
        </Text>
        <Menu>
          <MenuButton
            as={IconButton}
            icon={<FaUserCircle size={24} />}
            variant="ghost"
            aria-label="User menu"
          />
          <MenuList>
            <MenuItem onClick={() => signOut({ callbackUrl: '/' })}>
              Sign Out
            </MenuItem>
          </MenuList>
        </Menu>
      </Flex>
    </Box>
  )
} 