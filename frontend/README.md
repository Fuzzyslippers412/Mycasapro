MyCasa Pro frontend (Next.js App Router + Mantine).

## Getting Started

This frontend expects a running backend. Set the API URL first.

```bash
npm install
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:6709" > .env.local
npm run dev
```

Open http://localhost:3000

Backend must be running at `NEXT_PUBLIC_API_URL`.

See root docs for full setup:
- `../docs/INSTALL.md`
- `../docs/DEPLOY_VERCEL.md`

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
