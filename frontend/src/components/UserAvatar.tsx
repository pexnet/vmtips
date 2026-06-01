import { Avatar, type SxProps, type Theme } from "@mui/material";

function initialsFor(name?: string | null, email?: string | null): string {
  const source = (name || email || "?").trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }
  return source.slice(0, 2).toUpperCase();
}

interface UserAvatarProps {
  displayName?: string | null;
  firstName?: string | null;
  lastName?: string | null;
  email?: string | null;
  avatarUrl?: string | null;
  sx?: SxProps<Theme>;
}

export default function UserAvatar({
  displayName,
  firstName,
  lastName,
  email,
  avatarUrl,
  sx,
  ...props
}: UserAvatarProps) {
  return (
    <Avatar
      src={avatarUrl || undefined}
      alt={displayName || email || "User"}
      sx={[
        {
          bgcolor: "primary.main",
          color: "primary.contrastText",
          fontWeight: 800,
        },
        ...(Array.isArray(sx) ? sx : sx ? [sx] : []),
      ]}
      {...props}
    >
      {firstName && lastName
        ? `${firstName[0]}${lastName[0]}`.toUpperCase()
        : initialsFor(displayName, email)}
    </Avatar>
  );
}
