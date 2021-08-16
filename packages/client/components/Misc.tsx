import '@brainhubeu/react-carousel/lib/style.css';
import 'swiper/swiper-bundle.css';

import classNames from 'classnames';
import maxSize from 'popper-max-size-modifier';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import Editor from 'react-simple-code-editor';
import { useWindowScroll } from 'react-use';
import { useRecoilState } from 'recoil';
import {
  Button,
  Divider,
  Header,
  Icon,
  Input,
  Label,
  Message,
  Popup,
  Search,
  Segment,
} from 'semantic-ui-react';
import SwiperCore, { Autoplay, Navigation } from 'swiper/core';
import { Swiper, SwiperSlide } from 'swiper/react';



import { QueryType, useQueryType } from '../client/queries';
import { ItemType } from '../misc/enums';
import t from '../misc/lang';
import { ServerGallery, ServerItem } from '../misc/types';
import { parseMarkdown, scrollToTop } from '../misc/utility';
import { AppState, MiscState } from '../state';
import { useInitialRecoilState } from '../state/index';
import GalleryCard, { galleryCardDataFields } from './item/Gallery';
import styles from './Misc.module.css';

SwiperCore.use([Navigation, Autoplay]);

export function TextEditor({
  value,
  onChange,
}: {
  value?: string;
  onChange?: (value: string) => void;
}) {
  return (
    <Editor
      value={value}
      onValueChange={onChange}
      highlight={(s) => s}
      padding={10}
      style={{
        border: '1px solid rgba(34, 36, 38, 0.15)',
        background: 'rgba(0, 0, 0, 0.05) none repeat scroll 0% 0%',
        minHeight: '8em',
      }}
      placeholder="</ Text here ...>"
    />
  );
}

export function PageTitle({ title }: { title?: string }) {
  if (!global.app.IS_SERVER) {
    document.title = title
      ? title + ' - ' + global.app.title
      : global.app.title;
  }
  return null;
}

export function Markdown({ children }: { children?: string }) {
  return <div dangerouslySetInnerHTML={{ __html: parseMarkdown(children) }} />;
}

export function ScrollUpButton() {
  const { y } = useWindowScroll();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (y > 300) {
      if (!visible) {
        setVisible(true);
      }
    } else {
      if (visible) {
        setVisible(false);
      }
    }
  }, [y, visible]);

  return (
    <Visible visible={visible}>
      <Button onClick={scrollToTop} icon="chevron up" size="small" basic />
    </Visible>
  );
}

export function DrawerButton({ basic }: { basic?: boolean }) {
  const [open, setOpen] = useRecoilState(AppState.drawerOpen);

  return (
    <Visible visible={!open}>
      <Button
        primary
        circular
        basic={basic}
        onClick={useCallback(() => setOpen(true), [])}
        icon="window maximize outline"
        size="small"
      />
    </Visible>
  );
}

export function Visible({
  children,
  visible,
}: {
  children: React.ReactNode;
  visible?: boolean;
}): JSX.Element {
  return visible ? (children as any) : null;
}

export function TitleSegment({
  title,
  headerSize,
  children,
  as,
}: {
  title: string;
  as?: React.ElementType;
  headerSize?: React.ComponentProps<typeof Header>['size'];
  children?: React.ReactNode;
}) {
  return (
    <>
      <Header size={headerSize}>{title}</Header>
      <Segment as={as}>{children}</Segment>
    </>
  );
}

export function EmptySegment({
  title = t`Nothing to see here...`,
  description,
}: {
  title?: string;
  description?: string;
}) {
  return (
    <Segment placeholder disabled className="!min-0-h w-full h-full">
      <Header className="center text-center sub-text" icon>
        <Icon className="hpx-standard sub-text" size="huge" />
        {title}
        <Header.Subheader>{description}</Header.Subheader>
      </Header>
    </Segment>
  );
}

export function EmptyMessage({
  title = t`Nothing to see here...`,
  description,
}: {
  title?: string;
  description?: string;
}) {
  return (
    <Message>
      <Message.Header className="center text-center sub-text">
        {title}
      </Message.Header>
      <Message.Content className="text-center sub-text">
        {description}
        <Segment basic textAlign="center">
          <Icon className="hpx-standard sub-text" size="huge" />
        </Segment>
      </Message.Content>
    </Message>
  );
}

// export function Slider({
//   autoPlay,
//   children,
//   className,
//   ...props
// }: {
//   autoPlay?: boolean;
// } & React.ComponentProps<typeof Segment>) {
//   const items = React.Children.toArray(children);
//   return (
//     <Segment basic {...props} className={classNames('slider', className)}>
//       {!items.length && <EmptySegment />}
//       {items && (
//         <Carousel
//           autoPlay={autoPlay ?? false}
//           showThumbs={false}
//           showStatus={false}
//           centerMode
//           centerSlidePercentage={50}
//           emulateTouch
//           interval={10000}>
//           {children}
//         </Carousel>
//       )}
//     </Segment>
//   );
// }

function SliderNav({
  direction,
  onClick,
  disabled,
}: {
  direction: 'left' | 'right';
  disabled?: boolean;
  onClick?: Function;
}) {
  return (
    <Icon
      disabled={disabled}
      name={classNames('chevron', direction)}
      onClick={onClick}
      circular
      inverted
      link
      className={classNames(`slide-next-${direction}`, 'slide-next')}
    />
  );
}

export const SliderElement = SwiperSlide;

export function Slider({
  show: initialShow,
  defaultShow,
  stateKey,
  infinite,
  children,
  label,
  showCount = true,
  touchStartPreventDefault = false,
  color,
  autoplay,
  className,
  ...props
}: {
  show?: boolean;
  defaultShow?: boolean;
  stateKey?: string;
  infinite?: boolean;
  showCount?: boolean;
  touchStartPreventDefault?: boolean;
  autoplay?: boolean;
  label?: React.ReactNode;
} & React.ComponentProps<typeof Segment>) {
  const [open, setOpen] = useInitialRecoilState(
    MiscState.labelAccordionOpen(stateKey),
    initialShow ?? defaultShow
  );

  const swiper = useRef<SwiperCore>();

  const items = React.Children.toArray(children);

  useEffect(() => {
    if (swiper.current) {
      swiper.current.update();
    }
  }, [children]);

  return (
    <Segment basic {...props} className={classNames('slider', className)}>
      {!!label && (
        <Label
          color={color}
          attached="top"
          as={initialShow === false ? undefined : 'a'}
          onClick={useCallback(
            (e) => {
              e.preventDefault();
              if (initialShow === undefined) {
                setOpen(!open);
              }
            },
            [open]
          )}>
          <Icon name={open ? 'caret down' : 'caret right'} />
          {label}
          {showCount && <Label.Detail>{items.length}</Label.Detail>}
        </Label>
      )}
      <Visible visible={initialShow || open}>
        {!items.length && <EmptySegment />}
        {items && (
          <Swiper
            onSwiper={useCallback((s) => {
              swiper.current = s;
            }, [])}
            autoplay={useMemo(
              () =>
                autoplay
                  ? {
                      delay: 10000,
                      pauseOnMouseEnter: true,
                      stopOnLastSlide: false,
                    }
                  : undefined,
              [autoplay]
            )}
            loop={infinite}
            slidesPerView={3}
            touchStartPreventDefault={touchStartPreventDefault}
            navigation={useMemo(
              () => ({
                nextEl: '.slide-next-right',
                prevEl: '.slide-next-left',
              }),
              []
            )}
            breakpoints={useMemo(
              () => ({
                460: {
                  slidesPerView: 2,
                  slidesPerGroup: 2,
                },
                675: {
                  slidesPerView: 3,
                  slidesPerGroup: 3,
                },
                980: {
                  slidesPerView: 4,
                  slidesPerGroup: 3,
                },
                1200: {
                  slidesPerView: 5,
                  slidesPerGroup: 3,
                },
                1800: {
                  slidesPerView: 6,
                  slidesPerGroup: 3,
                },
              }),
              []
            )}>
            {children}
            <SliderNav direction="left" />
            <SliderNav direction="right" />
          </Swiper>
        )}
      </Visible>
    </Segment>
  );
}

export function LabelAccordion({
  stateKey,
  children,
  className,
  basic = true,
  label,
  detail,
  show: initialShow,
  defaultShow,
  color,
  attached = 'top',
  ...props
}: {
  stateKey?: string;
  show?: boolean;
  defaultShow?: boolean;
  attached?: React.ComponentProps<typeof Label>['attached'];
  color?: React.ComponentProps<typeof Label>['color'];
  label?: React.ReactNode;
  detail?: React.ReactNode;
} & React.ComponentProps<typeof Segment>) {
  const [show, setShow] = stateKey
    ? useInitialRecoilState(
        MiscState.labelAccordionOpen(stateKey),
        initialShow ?? defaultShow
      )
    : useState(initialShow ?? defaultShow);

  return (
    <Segment
      {...props}
      basic={basic}
      className={classNames('small-padding-segment', className)}>
      <Label
        as="a"
        color={color}
        attached={attached}
        onClick={useCallback(
          (e) => {
            e.preventDefault();
            if (initialShow === undefined) {
              setShow(!open);
            }
          },
          [open]
        )}>
        <Icon name={show ? 'caret down' : 'caret right'} />
        {label}
        {!!detail && <Label.Detail>{detail}</Label.Detail>}
      </Label>
      {show && children}
      {!show && <Divider hidden fitted />}
    </Segment>
  );
}

export function PageInfoMessage({
  props,
  className,
  color,
  hidden,
  size,
  onDismiss,
  children,
}: React.ComponentProps<typeof Message>) {
  return (
    <Message
      hidden={hidden}
      color={color}
      onDismiss={onDismiss}
      size={size}
      className={classNames(styles.pageinfo_message, className)}
      {...props}>
      {children}
    </Message>
  );
}

export function PopupNoOverflow(props: React.ComponentProps<typeof Popup>) {
  const applyMaxSize = useMemo(() => {
    return {
      name: 'applyMaxSize',
      enabled: true,
      phase: 'beforeWrite',
      requires: ['maxSize'],
      fn({ state }) {
        // The `maxSize` modifier provides this data
        const { width, height } = state.modifiersData.maxSize;

        state.styles.popper = {
          ...state.styles.popper,
          maxWidth: `${Math.max(100, width)}px`,
          maxHeight: `${Math.max(100, height)}px`,
        };
      },
    };
  }, []);

  return (
    <Popup
      {...props}
      offset={[20, 0]}
      popperModifiers={[maxSize, applyMaxSize]}
    />
  );
}

export function IdentityChildren({ children }) {
  return children;
}

export function ItemSearch({
  size,
  fluid,
  transparent = true,
  placeholder,
  defaultValue,
  onSearch,
  showOptions,
  onClear: cOnClear,
  className,
}: {
  fluid?: boolean;
  transparent?: boolean;
  defaultValue?: string;
  showOptions?: boolean;
  placeholder?: string;
  onSearch?: (query: string, options: object) => void;
  onClear?: () => void;
  size?: React.ComponentProps<typeof Search>['size'];
  className?: string;
}) {
  const [query, setQuery] = useState('');

  const onSubmit = useCallback(
    (ev) => {
      ev?.preventDefault?.();
      onSearch?.(query, {});
    },
    [query]
  );

  const onClear = useCallback(() => {
    setQuery('');
    cOnClear?.();
  }, [cOnClear]);

  return (
    <form
      onSubmit={onSubmit}
      className={classNames({ fullwidth: fluid }, className)}>
      <Search
        size={size}
        input={useMemo(
          () => (
            <Input
              fluid={fluid}
              className={classNames({ secondary: transparent })}
              placeholder={placeholder}
              label={
                showOptions ? (
                  <IdentityChildren>
                    <div>
                      <Popup
                        trigger={
                          <Button
                            basic
                            type="button"
                            size={size}
                            icon={
                              <Icon.Group>
                                <Icon name="options" />
                                <Icon name="search" corner />
                              </Icon.Group>
                            }
                          />
                        }
                        hoverable
                        on="click"
                        hideOnScroll>
                        options
                      </Popup>
                      {!!query && <Icon name="remove" link onClick={onClear} />}
                    </div>
                  </IdentityChildren>
                ) : undefined
              }
              icon={{ name: 'search', link: true, onClick: onSubmit }}
              tabIndex={0}
            />
          ),
          [size, onClear, query, onSubmit, showOptions, placeholder]
        )}
        minCharacters={2}
        onSearchChange={useCallback((ev, d) => {
          ev.preventDefault();
          setQuery(d.value);
        }, [])}
        fluid={fluid}
        value={query}
        defaultValue={defaultValue}
      />
    </form>
  );
}

export function SimilarItemsSlider({
  type,
  stateKey,
  item,
}: {
  type: ItemType;
  stateKey?: string;
  item: DeepPick<ServerItem, 'id'>;
}) {
  const { data, isLoading } = useQueryType(QueryType.SIMILAR, {
    item_id: item.id,
    item_type: type,
    fields: galleryCardDataFields,
    limit: 50,
  });

  return (
    <Slider
      autoplay
      loading={isLoading}
      stateKey={stateKey}
      showCount={false}
      label={t`Just like this one`}>
      {(data?.data.items as ServerGallery[])?.map?.((i) => (
        <SliderElement key={i.id}>
          <GalleryCard size="small" data={i} />
        </SliderElement>
      ))}
    </Slider>
  );
}
